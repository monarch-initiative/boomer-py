"""
SSSOM TSV solution renderer for boomer.

Renders a boomer Solution as a SSSOM (Simple Standard for Sharing
Ontological Mappings) TSV file. Only mapping-representable fact types
(EquivalentTo → skos:exactMatch, ProperSubClassOf → skos:narrowMatch)
are emitted; other fact types are silently skipped.

See https://mapping-commons.github.io/sssom/ for the specification.
"""

import csv
import datetime
from dataclasses import dataclass
from io import StringIO
from typing import Literal, Optional

from boomer.model import (
    EquivalentTo,
    KB,
    ProperSubClassOf,
    Solution,
    SolvedPFact,
)
from boomer.renderers.renderer import Renderer

# ---------------------------------------------------------------------------
# Fact type → SSSOM predicate (inverse of sssom_converter.PREDICATE_FACT_MAP)
# ---------------------------------------------------------------------------

FACT_PREDICATE_MAP: dict[str, str] = {
    "EquivalentTo": "skos:exactMatch",
    "ProperSubClassOf": "skos:narrowMatch",
}

# ---------------------------------------------------------------------------
# Well-known prefix → IRI map (extended as needed)
# ---------------------------------------------------------------------------

_KNOWN_PREFIX_MAP: dict[str, str] = {
    "HP": "http://purl.obolibrary.org/obo/HP_",
    "MP": "http://purl.obolibrary.org/obo/MP_",
    "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
    "OMIM": "https://omim.org/entry/",
    "ORDO": "http://www.orpha.net/ORDO/Orphanet_",
    "DOID": "http://purl.obolibrary.org/obo/DOID_",
    "NCIT": "http://purl.obolibrary.org/obo/NCIT_",
    "GO": "http://purl.obolibrary.org/obo/GO_",
    "CL": "http://purl.obolibrary.org/obo/CL_",
    "UBERON": "http://purl.obolibrary.org/obo/UBERON_",
    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
    "ZFA": "http://purl.obolibrary.org/obo/ZFA_",
    "FBbt": "http://purl.obolibrary.org/obo/FBbt_",
    "WBbt": "http://purl.obolibrary.org/obo/WBbt_",
    "MA": "http://purl.obolibrary.org/obo/MA_",
    "EMAPA": "http://purl.obolibrary.org/obo/EMAPA_",
    "BFO": "http://purl.obolibrary.org/obo/BFO_",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "semapv": "https://w3id.org/semapv/vocab/",
}

SSSOM_COLUMNS = [
    "subject_id",
    "subject_label",
    "predicate_id",
    "object_id",
    "object_label",
    "mapping_justification",
    "confidence",
]


def fact_to_sssom_row(
    spfact: SolvedPFact,
    labels: dict[str, str] | None = None,
) -> dict[str, str] | None:
    """Convert a SolvedPFact to an SSSOM row dict, or None if not mappable.

    Only ``EquivalentTo`` and ``ProperSubClassOf`` facts can be
    represented in SSSOM.

    >>> from boomer.model import PFact, EquivalentTo, SolvedPFact
    >>> sp = SolvedPFact(
    ...     pfact=PFact(fact=EquivalentTo(sub="A:1", equivalent="B:2"), prob=0.9),
    ...     truth_value=True,
    ...     posterior_prob=0.95,
    ... )
    >>> row = fact_to_sssom_row(sp)
    >>> row["predicate_id"]
    'skos:exactMatch'
    >>> row["subject_id"]
    'A:1'
    >>> row["object_id"]
    'B:2'
    >>> row["confidence"]
    '0.95'

    >>> from boomer.model import DisjointWith
    >>> sp2 = SolvedPFact(
    ...     pfact=PFact(fact=DisjointWith(sub="X:1", sibling="Y:2"), prob=0.5),
    ...     truth_value=True,
    ...     posterior_prob=0.6,
    ... )
    >>> fact_to_sssom_row(sp2) is None
    True
    """
    fact = spfact.pfact.fact
    fact_type = fact.__class__.__name__

    predicate = FACT_PREDICATE_MAP.get(fact_type)
    if predicate is None:
        return None

    if isinstance(fact, EquivalentTo):
        subject_id = fact.sub
        object_id = fact.equivalent
    elif isinstance(fact, ProperSubClassOf):
        subject_id = fact.sub
        object_id = fact.sup
    else:
        return None

    labels = labels or {}
    return {
        "subject_id": subject_id,
        "subject_label": labels.get(subject_id, ""),
        "predicate_id": predicate,
        "object_id": object_id,
        "object_label": labels.get(object_id, ""),
        "mapping_justification": "semapv:CompositeMatching",
        "confidence": str(spfact.posterior_prob),
    }


def _collect_prefixes(entities: set[str]) -> dict[str, str]:
    """Build a curie_map from entity prefixes present in the data."""
    curie_map: dict[str, str] = {}
    for entity in entities:
        parts = entity.split(":")
        if len(parts) >= 2:
            prefix = parts[0]
            if prefix in _KNOWN_PREFIX_MAP and prefix not in curie_map:
                curie_map[prefix] = _KNOWN_PREFIX_MAP[prefix]
    # Always include the standard predicate prefixes
    for p in ("skos", "semapv"):
        if p not in curie_map:
            curie_map[p] = _KNOWN_PREFIX_MAP[p]
    return dict(sorted(curie_map.items()))


@dataclass
class SSSOMRenderer(Renderer):
    """Render a boomer Solution as SSSOM TSV.

    Parameters
    ----------
    filter_mode : ``"accepted"`` or ``"all"``
        When ``"accepted"`` (default), only pfacts with
        ``truth_value=True`` are emitted. ``"all"`` emits every pfact.
    """

    filter_mode: Literal["accepted", "all"] = "accepted"

    def render(self, solution: Solution, kb: Optional[KB] = None) -> str:  # noqa: D102
        labels = kb.labels if kb else {}
        output = StringIO()

        # Collect rows first so we know which entities appear
        rows: list[dict[str, str]] = []
        entities: set[str] = set()
        for spf in solution.solved_pfacts:
            if self.filter_mode == "accepted" and not spf.truth_value:
                continue
            row = fact_to_sssom_row(spf, labels)
            if row is not None:
                rows.append(row)
                entities.add(row["subject_id"])
                entities.add(row["object_id"])

        curie_map = _collect_prefixes(entities)

        # --- YAML metadata header ---
        output.write("#mapping_set_id: boomer:solution\n")
        output.write("#mapping_tool: BOOMER\n")
        output.write(f"#mapping_date: {datetime.date.today().isoformat()}\n")
        if curie_map:
            output.write("#curie_map:\n")
            for prefix, iri in curie_map.items():
                output.write(f"#  {prefix}: {iri}\n")

        # --- TSV body ---
        writer = csv.DictWriter(
            output, fieldnames=SSSOM_COLUMNS, delimiter="\t", lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

        return output.getvalue()
