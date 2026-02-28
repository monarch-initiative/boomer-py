"""
Ontology-to-KB converter for boomer.

Converts OBO and OWL ontology files into boomer KB objects.
Structural axioms (is_a, equivalent_to, disjoint_from) become hard facts;
xrefs and SKOS mappings become probabilistic facts.

OBO parsing is hand-rolled with no external dependencies.
OWL support uses ``py-horned-owl``.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pyhornedowl
import yaml
from pydantic import BaseModel, Field
from pyhornedowl import model as owlmodel

from boomer.io import id_prefix
from boomer.model import (
    KB,
    DisjointWith,
    EquivalentTo,
    MemberOfDisjointGroup,
    PFact,
    ProperSubClassOf,
)
from boomer.sssom_converter import _make_fact

# ---------------------------------------------------------------------------
# OBO data model
# ---------------------------------------------------------------------------

QUALIFIER_RE = re.compile(r"\s*\{[^}]*\}")

SKOS_PREDICATES = frozenset({
    "skos:exactMatch",
    "skos:closeMatch",
    "skos:broadMatch",
    "skos:narrowMatch",
})


@dataclass
class OBOTerm:
    """A parsed OBO [Term] stanza."""

    id: str
    name: str | None = None
    is_obsolete: bool = False
    is_a: list[str] = field(default_factory=list)
    equivalent_to: list[str] = field(default_factory=list)
    disjoint_from: list[str] = field(default_factory=list)
    xrefs: list[str] = field(default_factory=list)
    skos_mappings: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class OBODocument:
    """A parsed OBO file."""

    ontology: str | None = None
    terms: list[OBOTerm] = field(default_factory=list)


# ---------------------------------------------------------------------------
# OBO parser
# ---------------------------------------------------------------------------


def _strip_comment(value: str) -> str:
    """Strip trailing ``! comment`` from an OBO tag value.

    >>> _strip_comment("TEST:0001 ! Root class")
    'TEST:0001'
    >>> _strip_comment("TEST:0001")
    'TEST:0001'
    """
    idx = value.find(" ! ")
    if idx >= 0:
        return value[:idx].strip()
    return value.strip()


def _strip_qualifiers(value: str) -> str:
    r"""Strip ``{qualifier}`` blocks from an OBO tag value.

    >>> _strip_qualifiers('EXT:R001 {source="manual"}')
    'EXT:R001'
    >>> _strip_qualifiers("EXT:R001")
    'EXT:R001'
    """
    return QUALIFIER_RE.sub("", value).strip()


def parse_obo(path: str | Path) -> OBODocument:
    """Parse an OBO format file into an :class:`OBODocument`.

    Only ``[Term]`` stanzas are parsed; ``[Typedef]`` and other stanza
    types are skipped. Recognised tags: ``id``, ``name``, ``is_a``,
    ``equivalent_to``, ``disjoint_from``, ``xref``, ``is_obsolete``,
    and ``property_value`` (for SKOS predicates).

    >>> doc = parse_obo("tests/input/test_ontology.obo")
    >>> doc.ontology
    'test-ontology'
    >>> len(doc.terms)
    5
    >>> doc.terms[0].id
    'TEST:0001'
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    doc = OBODocument()
    current_term: OBOTerm | None = None
    in_term = False

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        # Stanza headers
        if line.startswith("["):
            # Flush previous term
            if current_term is not None and current_term.id:
                doc.terms.append(current_term)
                current_term = None

            if line == "[Term]":
                current_term = OBOTerm(id="")
                in_term = True
            else:
                in_term = False
            continue

        # Tag: value lines
        if ":" not in line:
            continue

        tag, _, raw_value = line.partition(":")
        tag = tag.strip()
        raw_value = raw_value.strip()

        # Header tags (before any stanza)
        if not in_term:
            if tag == "ontology":
                doc.ontology = raw_value
            continue

        if current_term is None:
            continue

        # Term-level tags
        value = _strip_comment(raw_value)
        value = _strip_qualifiers(value)

        if tag == "id":
            current_term.id = value
        elif tag == "name":
            current_term.name = value
        elif tag == "is_a":
            current_term.is_a.append(value)
        elif tag == "equivalent_to":
            current_term.equivalent_to.append(value)
        elif tag == "disjoint_from":
            current_term.disjoint_from.append(value)
        elif tag == "xref":
            current_term.xrefs.append(value)
        elif tag == "is_obsolete":
            current_term.is_obsolete = value.lower() == "true"
        elif tag == "property_value":
            _parse_property_value(current_term, raw_value)

    # Flush last term
    if current_term is not None and current_term.id:
        doc.terms.append(current_term)

    return doc


def _parse_property_value(term: OBOTerm, raw_value: str) -> None:
    """Parse a ``property_value`` tag, extracting SKOS mappings."""
    parts = raw_value.split()
    if len(parts) < 2:
        return
    predicate = parts[0]
    if predicate in SKOS_PREDICATES:
        target = _strip_qualifiers(_strip_comment(parts[1]))
        # Skip data property_values (quoted string literals)
        if not target.startswith('"'):
            term.skos_mappings.append((predicate, target))


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class OntologyConverterConfig(BaseModel):
    """Configuration for ontology-to-KB conversion."""

    skos_exact_match_prob: float = 0.9
    skos_close_match_prob: float = 0.7
    skos_broad_match_prob: float = 0.7
    skos_narrow_match_prob: float = 0.7
    xref_default_probability: float = 0.7
    xref_prefix_probabilities: dict[str, float] = Field(default_factory=dict)
    skip_obsolete: bool = True
    include_xrefs: bool = True
    include_skos: bool = True
    auto_disjoint_groups: bool = True
    min_probability: float = 0.01


def load_ontology_config(path: str | Path) -> OntologyConverterConfig:
    """Load an :class:`OntologyConverterConfig` from a YAML file.

    >>> cfg = load_ontology_config("tests/input/ontology_config.yaml")
    >>> cfg.xref_default_probability
    0.8
    """
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return OntologyConverterConfig.model_validate(data)


# ---------------------------------------------------------------------------
# OBO → KB conversion
# ---------------------------------------------------------------------------

SKOS_PROB_MAP = {
    "skos:exactMatch": "skos_exact_match_prob",
    "skos:closeMatch": "skos_close_match_prob",
    "skos:broadMatch": "skos_broad_match_prob",
    "skos:narrowMatch": "skos_narrow_match_prob",
}


def obo_to_kb(
    path: str | Path,
    config: OntologyConverterConfig | None = None,
) -> KB:
    """Convert an OBO file into a boomer :class:`~boomer.model.KB`.

    Structural axioms become hard facts; xrefs and SKOS mappings become
    probabilistic facts.

    >>> kb = obo_to_kb("tests/input/test_ontology.obo")
    >>> kb.name
    'test-ontology'
    >>> len([f for f in kb.facts if f.fact_type == "ProperSubClassOf"])
    2
    >>> len(kb.pfacts) > 0
    True
    """
    if config is None:
        config = OntologyConverterConfig()

    doc = parse_obo(path)

    hard_facts: list = []
    pfacts: list[PFact] = []
    labels: dict[str, str] = {}
    seen_ids: set[str] = set()

    for term in doc.terms:
        if config.skip_obsolete and term.is_obsolete:
            continue

        # Labels
        if term.name:
            labels[term.id] = term.name

        seen_ids.add(term.id)

        # is_a → ProperSubClassOf hard fact
        for parent in term.is_a:
            hard_facts.append(ProperSubClassOf(sub=term.id, sup=parent))
            seen_ids.add(parent)

        # equivalent_to → EquivalentTo hard fact
        for equiv in term.equivalent_to:
            hard_facts.append(EquivalentTo(sub=term.id, equivalent=equiv))
            seen_ids.add(equiv)

        # disjoint_from → DisjointWith hard fact
        for disj in term.disjoint_from:
            hard_facts.append(DisjointWith(sub=term.id, sibling=disj))
            seen_ids.add(disj)

        # xrefs → pfacts
        if config.include_xrefs:
            for xref in term.xrefs:
                prefix = xref.split(":")[0] if ":" in xref else ""
                prob = config.xref_prefix_probabilities.get(
                    prefix, config.xref_default_probability
                )
                if prob >= config.min_probability:
                    pfacts.append(
                        PFact(
                            fact=EquivalentTo(sub=term.id, equivalent=xref),
                            prob=prob,
                        )
                    )
                    seen_ids.add(xref)

        # SKOS mappings → pfacts via _make_fact
        if config.include_skos:
            for predicate, target in term.skos_mappings:
                prob_attr = SKOS_PROB_MAP.get(predicate)
                if prob_attr is None:
                    continue
                prob = getattr(config, prob_attr)
                if prob < config.min_probability:
                    continue
                fact = _make_fact(predicate, term.id, target)
                if fact is not None:
                    pfacts.append(PFact(fact=fact, prob=prob))
                    seen_ids.add(target)

    # Auto MemberOfDisjointGroup per prefix
    if config.auto_disjoint_groups:
        for eid in seen_ids:
            if ":" in eid:
                prefix = id_prefix(eid)
                hard_facts.append(MemberOfDisjointGroup(sub=eid, group=prefix))

    return KB(
        facts=hard_facts,
        pfacts=pfacts,
        labels=labels,
        name=doc.ontology,
    )


# ---------------------------------------------------------------------------
# OWL → KB conversion (py-horned-owl)
# ---------------------------------------------------------------------------

# OBO-style IRI pattern: http://purl.obolibrary.org/obo/GO_0008150 → GO:0008150
_OBO_IRI_RE = re.compile(r"^http://purl\.obolibrary\.org/obo/(\w+?)_(.+)$")

# Common annotation property IRIs
_RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
_HAS_DBXREF = "http://www.geneontology.org/formats/oboInOwl#hasDbXref"
_SKOS_EXACT = "http://www.w3.org/2004/02/skos/core#exactMatch"
_SKOS_CLOSE = "http://www.w3.org/2004/02/skos/core#closeMatch"
_SKOS_BROAD = "http://www.w3.org/2004/02/skos/core#broadMatch"
_SKOS_NARROW = "http://www.w3.org/2004/02/skos/core#narrowMatch"

_SKOS_IRI_MAP = {
    _SKOS_EXACT: "skos:exactMatch",
    _SKOS_CLOSE: "skos:closeMatch",
    _SKOS_BROAD: "skos:broadMatch",
    _SKOS_NARROW: "skos:narrowMatch",
}


def _iri_to_curie(iri: str, prefix_map: dict[str, str] | None = None) -> str:
    """Convert an IRI to a CURIE using prefix mappings or OBO conventions.

    >>> _iri_to_curie("http://purl.obolibrary.org/obo/GO_0008150")
    'GO:0008150'
    >>> _iri_to_curie("http://example.org/FOO")
    'http://example.org/FOO'
    """
    # Try OBO-style IRI
    m = _OBO_IRI_RE.match(iri)
    if m:
        return f"{m.group(1)}:{m.group(2)}"

    # Try prefix map
    if prefix_map:
        for prefix, ns in prefix_map.items():
            if iri.startswith(ns):
                local = iri[len(ns):]
                return f"{prefix}:{local}"

    return iri


def owl_to_kb(
    path: str | Path,
    config: OntologyConverterConfig | None = None,
) -> KB:
    """Convert an OWL file into a boomer :class:`~boomer.model.KB`.

    Extracts SubClassOf, EquivalentClasses, DisjointClasses axioms as
    hard facts, and annotation assertions for labels, xrefs, and SKOS
    mappings.

    Args:
        path: Path to the OWL file (.owl, .owx, .ofn).
        config: Optional converter configuration.

    Returns:
        A :class:`~boomer.model.KB` ready for probabilistic reasoning.
    """
    if config is None:
        config = OntologyConverterConfig()

    onto = pyhornedowl.open_ontology(str(path))

    # Build prefix map from ontology (filter out empty prefix)
    prefix_map: dict[str, str] = {
        k: v for k, v in dict(onto.prefix_mapping).items() if k
    }

    def curie(iri_or_str) -> str:
        iri_str = str(iri_or_str)
        # Strip angle brackets if present
        if iri_str.startswith("<") and iri_str.endswith(">"):
            iri_str = iri_str[1:-1]
        return _iri_to_curie(iri_str, prefix_map)

    def is_named_class(expr) -> bool:
        return isinstance(expr, owlmodel.Class)

    hard_facts: list = []
    pfacts: list[PFact] = []
    labels: dict[str, str] = {}
    seen_ids: set[str] = set()

    for annotated in onto.get_axioms():
        ax = annotated.component

        # SubClassOf(Class, Class) → ProperSubClassOf
        if isinstance(ax, owlmodel.SubClassOf):
            if is_named_class(ax.sub) and is_named_class(ax.sup):
                sub_id = curie(ax.sub.first)
                sup_id = curie(ax.sup.first)
                hard_facts.append(ProperSubClassOf(sub=sub_id, sup=sup_id))
                seen_ids.update([sub_id, sup_id])

        # EquivalentClasses → pairwise EquivalentTo
        elif isinstance(ax, owlmodel.EquivalentClasses):
            named = [curie(c.first) for c in ax.first if is_named_class(c)]
            for i, a in enumerate(named):
                for b in named[i + 1:]:
                    hard_facts.append(EquivalentTo(sub=a, equivalent=b))
                    seen_ids.update([a, b])

        # DisjointClasses → DisjointWith (pairwise)
        elif isinstance(ax, owlmodel.DisjointClasses):
            named = [curie(c.first) for c in ax.first if is_named_class(c)]
            for i, a in enumerate(named):
                for b in named[i + 1:]:
                    hard_facts.append(DisjointWith(sub=a, sibling=b))
                    seen_ids.update([a, b])

        # AnnotationAssertion
        elif isinstance(ax, owlmodel.AnnotationAssertion):
            prop_iri = str(ax.ann.ap.first)
            subject_iri = str(ax.subject)
            subject_id = _iri_to_curie(subject_iri, prefix_map)

            # rdfs:label
            if prop_iri == _RDFS_LABEL:
                ann_val = ax.ann.av
                if isinstance(ann_val, (owlmodel.SimpleLiteral, owlmodel.Literal)):
                    label_str = str(ann_val.literal)
                    if label_str:
                        labels[subject_id] = label_str
                        seen_ids.add(subject_id)

            # oboInOwl:hasDbXref → xref pfact
            elif prop_iri == _HAS_DBXREF and config.include_xrefs:
                ann_val = ax.ann.av
                val_str = ""
                if isinstance(ann_val, (owlmodel.SimpleLiteral, owlmodel.Literal)):
                    val_str = str(ann_val.literal)
                elif isinstance(ann_val, owlmodel.IRI):
                    val_str = _iri_to_curie(str(ann_val), prefix_map)
                if val_str and ":" in val_str:
                    prefix = val_str.split(":")[0]
                    prob = config.xref_prefix_probabilities.get(
                        prefix, config.xref_default_probability
                    )
                    if prob >= config.min_probability:
                        pfacts.append(
                            PFact(
                                fact=EquivalentTo(sub=subject_id, equivalent=val_str),
                                prob=prob,
                            )
                        )
                        seen_ids.update([subject_id, val_str])

            # SKOS mapping predicates
            elif prop_iri in _SKOS_IRI_MAP and config.include_skos:
                skos_pred = _SKOS_IRI_MAP[prop_iri]
                ann_val = ax.ann.av
                target = ""
                if isinstance(ann_val, owlmodel.IRI):
                    target = _iri_to_curie(str(ann_val), prefix_map)
                elif isinstance(ann_val, (owlmodel.SimpleLiteral, owlmodel.Literal)):
                    target = str(ann_val.literal)
                if target:
                    prob_attr = SKOS_PROB_MAP.get(skos_pred)
                    if prob_attr:
                        prob = getattr(config, prob_attr)
                        if prob >= config.min_probability:
                            fact = _make_fact(skos_pred, subject_id, target)
                            if fact is not None:
                                pfacts.append(PFact(fact=fact, prob=prob))
                                seen_ids.update([subject_id, target])

    # Auto MemberOfDisjointGroup per prefix
    if config.auto_disjoint_groups:
        for eid in seen_ids:
            if ":" in eid:
                prefix = id_prefix(eid)
                hard_facts.append(MemberOfDisjointGroup(sub=eid, group=prefix))

    # Derive name from ontology IRI
    onto_iri = onto.get_iri()
    name = str(onto_iri) if onto_iri else Path(path).stem

    return KB(
        facts=hard_facts,
        pfacts=pfacts,
        labels=labels,
        name=name,
    )


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def ontology_to_kb(
    path: str | Path,
    config: OntologyConverterConfig | None = None,
) -> KB:
    """Convert an ontology file to a boomer KB, dispatching by extension.

    >>> kb = ontology_to_kb("tests/input/test_ontology.obo")
    >>> kb.name
    'test-ontology'
    """
    ext = Path(path).suffix.lower()
    if ext == ".obo":
        return obo_to_kb(path, config)
    elif ext in (".owl", ".owx", ".ofn"):
        return owl_to_kb(path, config)
    else:
        raise ValueError(f"Unrecognized ontology extension: {ext!r}")
