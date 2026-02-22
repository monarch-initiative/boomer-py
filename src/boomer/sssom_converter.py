"""
SSSOM (Simple Standard for Sharing Ontological Mappings) converter for boomer.

Converts SSSOM TSV files into boomer KB objects for probabilistic ontology alignment.

The SSSOM format uses lines starting with ``#`` for YAML metadata, followed by a
TSV header row and data rows. This module parses that format and converts mappings
into boomer's probabilistic fact representation.

See https://mapping-commons.github.io/sssom/ for the SSSOM specification.
"""

import csv
import io
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from boomer.io import id_prefix
from boomer.model import (
    KB,
    EquivalentTo,
    MemberOfDisjointGroup,
    PFact,
    ProperSubClassOf,
)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

ConfidenceTransformFn = Callable[[float], float]

# ---------------------------------------------------------------------------
# Constants: predicate -> boomer fact type mapping
# ---------------------------------------------------------------------------

PREDICATE_FACT_MAP: dict[str, str] = {
    "skos:exactMatch": "EquivalentTo",
    "skos:closeMatch": "EquivalentTo",
    "skos:broadMatch": "ProperSubClassOf",
    "skos:narrowMatch": "ProperSubClassOf",
    "owl:equivalentClass": "EquivalentTo",
    "rdfs:subClassOf": "ProperSubClassOf",
}

DEFAULT_PREDICATE_PROBS: dict[str, float] = {
    "skos:exactMatch": 0.9,
    "skos:closeMatch": 0.7,
    "skos:broadMatch": 0.7,
    "skos:narrowMatch": 0.7,
    "owl:equivalentClass": 0.9,
    "rdfs:subClassOf": 0.8,
}

# ---------------------------------------------------------------------------
# Confidence transforms
# ---------------------------------------------------------------------------


def identity_transform(confidence: float) -> float:
    """Return confidence unchanged.

    >>> identity_transform(0.42)
    0.42
    >>> identity_transform(0.0)
    0.0
    """
    return confidence


def floor_ceil_transform(floor: float, ceil: float) -> ConfidenceTransformFn:
    """Return a clamping function that restricts confidence to ``[floor, ceil]``.

    >>> clamp = floor_ceil_transform(0.1, 0.9)
    >>> clamp(0.05)
    0.1
    >>> clamp(0.5)
    0.5
    >>> clamp(0.95)
    0.9
    """

    def _clamp(confidence: float) -> float:
        if confidence < floor:
            return floor
        if confidence > ceil:
            return ceil
        return confidence

    return _clamp


def rescale_transform(low: float, high: float) -> ConfidenceTransformFn:
    """Return a linear rescaling function: ``low + confidence * (high - low)``.

    >>> scale = rescale_transform(0.1, 0.9)
    >>> scale(0.0)
    0.1
    >>> scale(1.0)
    0.9
    >>> scale(0.5)
    0.5
    """

    def _rescale(confidence: float) -> float:
        return low + confidence * (high - low)

    return _rescale


# ---------------------------------------------------------------------------
# Named transform registry
# ---------------------------------------------------------------------------

NAMED_TRANSFORMS: dict[str, Callable[..., ConfidenceTransformFn]] = {
    "identity": lambda: identity_transform,
    "floor_ceil": lambda floor=0.01, ceil=0.99: floor_ceil_transform(floor, ceil),
    "rescale": lambda low=0.1, high=0.9: rescale_transform(low, high),
}


def _resolve_transform(
    name: str | None,
    params: dict[str, float] | None,
) -> ConfidenceTransformFn:
    """Look up a named transform and return the concrete function.

    >>> fn = _resolve_transform("identity", None)
    >>> fn(0.5)
    0.5
    >>> fn2 = _resolve_transform("rescale", {"low": 0.2, "high": 0.8})
    >>> fn2(0.0)
    0.2
    """
    if name is None:
        name = "identity"
    factory = NAMED_TRANSFORMS.get(name)
    if factory is None:
        raise ValueError(
            f"Unknown confidence transform: {name!r}. "
            f"Available: {sorted(NAMED_TRANSFORMS)}"
        )
    return factory(**(params or {}))


# ---------------------------------------------------------------------------
# Config models
# ---------------------------------------------------------------------------


class MappingRule(BaseModel):
    """A rule that selects SSSOM rows and optionally overrides probability.

    Each field acts as a filter: only non-``None`` fields are checked.
    Source fields use **prefix** matching against the ID prefix (the part
    before the first ``:``) of the corresponding SSSOM column.

    >>> rule = MappingRule(subject_source="OMIM", probability=0.6)
    >>> rule.matches({"subject_id": "OMIM:100100", "object_id": "MONDO:123"})
    True
    >>> rule.matches({"subject_id": "ORDO:123", "object_id": "MONDO:123"})
    False
    """

    subject_source: str | None = None
    object_source: str | None = None
    predicate_id: str | None = None
    mapping_justification: str | None = None
    probability: float | None = None
    confidence_transform: str | None = None
    transform_params: dict[str, float] | None = None
    skip: bool = False

    def matches(self, row: dict[str, str]) -> bool:
        """Return ``True`` if this rule matches *row*.

        A rule matches when every non-``None`` filter field matches the
        corresponding value in *row*.  Source fields match by checking
        whether the ID in the row starts with ``<source>:``.

        >>> rule = MappingRule(predicate_id="skos:exactMatch")
        >>> rule.matches({"predicate_id": "skos:exactMatch", "subject_id": "X:1"})
        True
        >>> rule.matches({"predicate_id": "skos:broadMatch", "subject_id": "X:1"})
        False
        """
        if self.subject_source is not None:
            sid = row.get("subject_id", "")
            if not sid.startswith(f"{self.subject_source}:"):
                return False
        if self.object_source is not None:
            oid = row.get("object_id", "")
            if not oid.startswith(f"{self.object_source}:"):
                return False
        if self.predicate_id is not None:
            if row.get("predicate_id") != self.predicate_id:
                return False
        if self.mapping_justification is not None:
            if row.get("mapping_justification") != self.mapping_justification:
                return False
        return True


class SSSOMConverterConfig(BaseModel):
    """Configuration for the SSSOM-to-KB conversion pipeline.

    >>> cfg = SSSOMConverterConfig()
    >>> cfg.predicate_defaults["skos:exactMatch"]
    0.9
    >>> cfg.auto_disjoint_groups
    True
    """

    predicate_defaults: dict[str, float] = Field(
        default_factory=lambda: dict(DEFAULT_PREDICATE_PROBS),
    )
    default_confidence_transform: str = "identity"
    default_transform_params: dict[str, float] | None = None
    rules: list[MappingRule] = Field(default_factory=list)
    auto_disjoint_groups: bool = True
    min_probability: float = 0.01
    subject_prefixes: list[str] | None = None
    object_prefixes: list[str] | None = None


# ---------------------------------------------------------------------------
# SSSOM TSV parser
# ---------------------------------------------------------------------------


def parse_sssom_tsv(path: str | Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Parse a SSSOM TSV file into metadata and row dicts.

    SSSOM files have an optional YAML metadata header where every line
    starts with ``#``, followed by a TSV section with a header row and
    data rows.

    Args:
        path: Path to the SSSOM TSV file.

    Returns:
        A ``(metadata, rows)`` tuple where *metadata* is a dict parsed
        from the YAML header lines and *rows* is a list of dicts keyed
        by the TSV column headers.

    >>> import tempfile, os
    >>> content = (
    ...     "#mapping_set_id: https://example.org/demo\\n"
    ...     "subject_id\\tobject_id\\tpredicate_id\\n"
    ...     "A:1\\tB:2\\tskos:exactMatch\\n"
    ... )
    >>> p = tempfile.NamedTemporaryFile(mode="w", suffix=".sssom.tsv", delete=False)
    >>> _ = p.write(content)
    >>> p.close()
    >>> meta, rows = parse_sssom_tsv(p.name)
    >>> meta["mapping_set_id"]
    'https://example.org/demo'
    >>> len(rows)
    1
    >>> rows[0]["subject_id"]
    'A:1'
    >>> os.unlink(p.name)
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    meta_lines: list[str] = []
    tsv_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("#"):
            # Strip leading '#' (and optional space) to get YAML content
            meta_lines.append(line[1:])
        else:
            tsv_lines.append(line)

    # Parse YAML metadata
    metadata: dict[str, Any] = {}
    if meta_lines:
        yaml_text = "\n".join(meta_lines)
        parsed = yaml.safe_load(yaml_text)
        if isinstance(parsed, dict):
            metadata = parsed

    # Parse TSV rows
    tsv_text = "\n".join(tsv_lines)
    reader = csv.DictReader(io.StringIO(tsv_text), delimiter="\t")
    rows = list(reader)

    return metadata, rows


# ---------------------------------------------------------------------------
# Fact construction
# ---------------------------------------------------------------------------


def _make_fact(
    predicate_id: str,
    subject_id: str,
    object_id: str,
) -> EquivalentTo | ProperSubClassOf | None:
    """Create a boomer ``Fact`` from an SSSOM predicate and entity pair.

    ``skos:broadMatch`` reverses subject/object for ``ProperSubClassOf``
    because "A broadMatch B" means A is broader, i.e. B subClassOf A.

    Returns ``None`` for unrecognised predicates.

    >>> _make_fact("skos:exactMatch", "A:1", "B:2")
    EquivalentTo(fact_type='EquivalentTo', sub='A:1', equivalent='B:2')
    >>> _make_fact("skos:broadMatch", "A:1", "B:2")
    ProperSubClassOf(fact_type='ProperSubClassOf', sub='B:2', sup='A:1')
    >>> _make_fact("skos:narrowMatch", "A:1", "B:2")
    ProperSubClassOf(fact_type='ProperSubClassOf', sub='A:1', sup='B:2')
    >>> _make_fact("skos:relatedMatch", "A:1", "B:2") is None
    True
    """
    fact_type = PREDICATE_FACT_MAP.get(predicate_id)
    if fact_type is None:
        return None

    if fact_type == "EquivalentTo":
        return EquivalentTo(sub=subject_id, equivalent=object_id)

    # ProperSubClassOf
    if predicate_id == "skos:broadMatch":
        # "A broadMatch B" means B is more specific: B subClassOf A
        return ProperSubClassOf(sub=object_id, sup=subject_id)
    if predicate_id == "skos:narrowMatch":
        # "A narrowMatch B" means A is more specific: A subClassOf B
        return ProperSubClassOf(sub=subject_id, sup=object_id)
    if predicate_id == "rdfs:subClassOf":
        return ProperSubClassOf(sub=subject_id, sup=object_id)

    # Shouldn't reach here, but be safe
    return ProperSubClassOf(sub=subject_id, sup=object_id)


# ---------------------------------------------------------------------------
# Row-level conversion
# ---------------------------------------------------------------------------


def sssom_mappings_to_pfacts(
    rows: list[dict[str, str]],
    config: SSSOMConverterConfig | None = None,
) -> list[PFact]:
    """Convert parsed SSSOM rows to a list of boomer ``PFact`` objects.

    The conversion pipeline for each row is:

    1. Apply prefix filters from *config* (``subject_prefixes`` / ``object_prefixes``).
    2. Find the first matching rule in ``config.rules``.
    3. Skip the row if the matching rule says ``skip=True``.
    4. Create a ``Fact`` via :func:`_make_fact`.
    5. Determine probability: rule override > confidence column (with
       transform) > predicate default.
    6. Drop if below ``config.min_probability``.

    >>> rows = [
    ...     {"subject_id": "A:1", "object_id": "B:2",
    ...      "predicate_id": "skos:exactMatch", "confidence": "0.85"},
    ... ]
    >>> pfacts = sssom_mappings_to_pfacts(rows)
    >>> len(pfacts)
    1
    >>> pfacts[0].prob
    0.85
    >>> pfacts[0].fact
    EquivalentTo(fact_type='EquivalentTo', sub='A:1', equivalent='B:2')
    """
    if config is None:
        config = SSSOMConverterConfig()

    pfacts: list[PFact] = []
    default_transform = _resolve_transform(
        config.default_confidence_transform,
        config.default_transform_params,
    )

    for row in rows:
        subject_id = row.get("subject_id", "")
        object_id = row.get("object_id", "")
        predicate_id = row.get("predicate_id", "")

        # 1. Apply prefix filters
        if config.subject_prefixes is not None:
            subj_prefix = subject_id.split(":")[0] if ":" in subject_id else ""
            if subj_prefix not in config.subject_prefixes:
                continue
        if config.object_prefixes is not None:
            obj_prefix = object_id.split(":")[0] if ":" in object_id else ""
            if obj_prefix not in config.object_prefixes:
                continue

        # 2. Find first matching rule
        matched_rule: MappingRule | None = None
        for rule in config.rules:
            if rule.matches(row):
                matched_rule = rule
                break

        # 3. Skip if rule says skip
        if matched_rule is not None and matched_rule.skip:
            continue

        # 4. Create fact
        fact = _make_fact(predicate_id, subject_id, object_id)
        if fact is None:
            continue

        # 5. Determine probability
        prob: float | None = None

        if matched_rule is not None and matched_rule.probability is not None:
            # Rule override
            prob = matched_rule.probability
        else:
            # Try confidence column with transform
            raw_confidence = row.get("confidence", "").strip()
            if raw_confidence:
                confidence_val = float(raw_confidence)
                # Pick transform: rule-specific > default
                if matched_rule is not None and matched_rule.confidence_transform is not None:
                    transform = _resolve_transform(
                        matched_rule.confidence_transform,
                        matched_rule.transform_params,
                    )
                else:
                    transform = default_transform
                prob = transform(confidence_val)
            else:
                # Fall back to predicate default
                prob = config.predicate_defaults.get(predicate_id)

        if prob is None:
            continue

        # 6. Drop if below min_probability
        if prob < config.min_probability:
            continue

        pfacts.append(PFact(fact=fact, prob=prob))

    return pfacts


# ---------------------------------------------------------------------------
# Top-level conversion
# ---------------------------------------------------------------------------


def sssom_to_kb(
    path: str | Path,
    config: SSSOMConverterConfig | None = None,
) -> KB:
    """Convert an SSSOM TSV file into a boomer ``KB``.

    This is the main entry point for SSSOM import. It:

    1. Parses the SSSOM TSV file.
    2. Converts rows to ``PFact`` objects.
    3. Extracts labels from ``subject_label`` / ``object_label`` columns.
    4. Auto-generates ``MemberOfDisjointGroup`` facts from ID prefixes
       (when ``config.auto_disjoint_groups`` is ``True``).
    5. Uses SSSOM metadata for KB ``name`` / ``description``.

    Args:
        path: Path to the SSSOM TSV file.
        config: Optional converter configuration.

    Returns:
        A :class:`~boomer.model.KB` ready for probabilistic reasoning.

    >>> import tempfile, os
    >>> content = (
    ...     "#mapping_set_id: https://example.org/demo\\n"
    ...     "#mapping_set_description: Demo mappings\\n"
    ...     "subject_id\\tsubject_label\\tobject_id\\tobject_label\\tpredicate_id\\tconfidence\\n"
    ...     "X:1\\tFoo\\tY:2\\tBar\\tskos:exactMatch\\t0.9\\n"
    ... )
    >>> p = tempfile.NamedTemporaryFile(mode="w", suffix=".sssom.tsv", delete=False)
    >>> _ = p.write(content)
    >>> p.close()
    >>> kb = sssom_to_kb(p.name)
    >>> kb.name
    'https://example.org/demo'
    >>> kb.description
    'Demo mappings'
    >>> len(kb.pfacts)
    1
    >>> kb.labels["X:1"]
    'Foo'
    >>> len(kb.facts)
    2
    >>> os.unlink(p.name)
    """
    if config is None:
        config = SSSOMConverterConfig()

    metadata, rows = parse_sssom_tsv(path)

    # Convert to pfacts
    pfacts = sssom_mappings_to_pfacts(rows, config)

    # Extract labels
    labels: dict[str, str] = {}
    for row in rows:
        subject_id = row.get("subject_id", "")
        subject_label = row.get("subject_label", "").strip()
        object_id = row.get("object_id", "")
        object_label = row.get("object_label", "").strip()
        if subject_id and subject_label:
            labels[subject_id] = subject_label
        if object_id and object_label:
            labels[object_id] = object_label

    # Auto-generate MemberOfDisjointGroup facts
    facts: list[MemberOfDisjointGroup] = []
    if config.auto_disjoint_groups:
        seen_ids: set[str] = set()
        for row in rows:
            for col in ("subject_id", "object_id"):
                eid = row.get(col, "")
                if eid and eid not in seen_ids and ":" in eid:
                    seen_ids.add(eid)
                    prefix = id_prefix(eid)
                    facts.append(MemberOfDisjointGroup(sub=eid, group=prefix))

    # Use SSSOM metadata for KB name/description
    name = metadata.get("mapping_set_id")
    description = metadata.get("mapping_set_description")

    return KB(
        facts=facts,
        pfacts=pfacts,
        labels=labels,
        name=name,
        description=description,
    )


# ---------------------------------------------------------------------------
# Config file I/O
# ---------------------------------------------------------------------------


def load_sssom_config(path: str | Path) -> SSSOMConverterConfig:
    """Load a :class:`SSSOMConverterConfig` from a YAML file.

    >>> config = load_sssom_config("tests/input/sssom_config.yaml")
    >>> config.predicate_defaults["skos:exactMatch"]
    0.85
    >>> len(config.rules)
    2
    """
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return SSSOMConverterConfig.model_validate(data)
