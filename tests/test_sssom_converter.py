"""Tests for the SSSOM converter module."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from boomer.model import (
    EquivalentTo,
    KB,
    MemberOfDisjointGroup,
    ProperSubClassOf,
)
from boomer.sssom_converter import (
    DEFAULT_PREDICATE_PROBS,
    MappingRule,
    SSSOMConverterConfig,
    _make_fact,
    _resolve_transform,
    floor_ceil_transform,
    identity_transform,
    load_sssom_config,
    parse_sssom_tsv,
    rescale_transform,
    sssom_mappings_to_pfacts,
    sssom_to_kb,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SSSOM_FILE = Path(__file__).parent / "input" / "test_mappings.sssom.tsv"


def _write_sssom(content: str) -> str:
    """Write SSSOM content to a temp file and return the path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".sssom.tsv", delete=False, encoding="utf-8",
    )
    f.write(content)
    f.close()
    return f.name


# =========================================================================
# Task 1: SSSOM TSV parser
# =========================================================================


class TestParseSssomTsv:
    """Tests for parse_sssom_tsv()."""

    def test_parse_fixture_metadata(self):
        metadata, rows = parse_sssom_tsv(SSSOM_FILE)
        assert metadata["mapping_set_id"] == "https://example.org/test_mappings"
        assert metadata["mapping_set_description"] == "Test mappings for boomer SSSOM converter"
        assert "curie_map" in metadata

    def test_parse_fixture_rows(self):
        _, rows = parse_sssom_tsv(SSSOM_FILE)
        assert len(rows) == 5
        assert rows[0]["subject_id"] == "ORDO:123"
        assert rows[0]["subject_label"] == "Alpha disease"
        assert rows[0]["predicate_id"] == "skos:exactMatch"
        assert rows[0]["object_id"] == "MONDO:0001234"
        assert rows[0]["confidence"] == "0.95"

    def test_parse_no_metadata(self):
        path = _write_sssom(
            "subject_id\tobject_id\n"
            "A:1\tB:2\n"
        )
        metadata, rows = parse_sssom_tsv(path)
        assert metadata == {}
        assert len(rows) == 1
        os.unlink(path)

    def test_parse_empty_metadata(self):
        path = _write_sssom(
            "# just a comment that is not valid yaml mapping\n"
            "subject_id\tobject_id\n"
            "A:1\tB:2\n"
        )
        metadata, rows = parse_sssom_tsv(path)
        # A bare string in yaml parses as a string, not a dict
        assert isinstance(metadata, dict)
        assert len(rows) == 1
        os.unlink(path)


# =========================================================================
# Task 2: Confidence transforms
# =========================================================================


class TestIdentityTransform:
    @pytest.mark.parametrize("val", [0.0, 0.5, 1.0, 0.123])
    def test_passthrough(self, val: float):
        assert identity_transform(val) == val


class TestFloorCeilTransform:
    @pytest.mark.parametrize(
        "floor, ceil, inp, expected",
        [
            (0.1, 0.9, 0.05, 0.1),
            (0.1, 0.9, 0.5, 0.5),
            (0.1, 0.9, 0.95, 0.9),
            (0.1, 0.9, 0.1, 0.1),
            (0.1, 0.9, 0.9, 0.9),
            (0.0, 1.0, 0.5, 0.5),
            (0.3, 0.7, 0.0, 0.3),
            (0.3, 0.7, 1.0, 0.7),
        ],
    )
    def test_clamp(self, floor: float, ceil: float, inp: float, expected: float):
        fn = floor_ceil_transform(floor, ceil)
        assert fn(inp) == pytest.approx(expected)


class TestRescaleTransform:
    @pytest.mark.parametrize(
        "low, high, inp, expected",
        [
            (0.1, 0.9, 0.0, 0.1),
            (0.1, 0.9, 1.0, 0.9),
            (0.1, 0.9, 0.5, 0.5),
            (0.2, 0.8, 0.0, 0.2),
            (0.2, 0.8, 1.0, 0.8),
            (0.0, 1.0, 0.5, 0.5),
        ],
    )
    def test_rescale(self, low: float, high: float, inp: float, expected: float):
        fn = rescale_transform(low, high)
        assert fn(inp) == pytest.approx(expected)


class TestResolveTransform:
    def test_identity(self):
        fn = _resolve_transform("identity", None)
        assert fn(0.42) == 0.42

    def test_floor_ceil(self):
        fn = _resolve_transform("floor_ceil", {"floor": 0.1, "ceil": 0.9})
        assert fn(0.05) == 0.1
        assert fn(0.95) == 0.9

    def test_rescale(self):
        fn = _resolve_transform("rescale", {"low": 0.2, "high": 0.8})
        assert fn(0.0) == pytest.approx(0.2)
        assert fn(1.0) == pytest.approx(0.8)

    def test_none_defaults_to_identity(self):
        fn = _resolve_transform(None, None)
        assert fn(0.7) == 0.7

    def test_unknown_transform_raises(self):
        with pytest.raises(ValueError, match="Unknown confidence transform"):
            _resolve_transform("nonexistent", None)


# =========================================================================
# Task 3: Config model and mapping rules
# =========================================================================


class TestMappingRule:
    def test_matches_subject_source(self):
        rule = MappingRule(subject_source="OMIM")
        assert rule.matches({"subject_id": "OMIM:100100", "object_id": "MONDO:123"})
        assert not rule.matches({"subject_id": "ORDO:123", "object_id": "MONDO:123"})

    def test_matches_object_source(self):
        rule = MappingRule(object_source="MONDO")
        assert rule.matches({"subject_id": "X:1", "object_id": "MONDO:123"})
        assert not rule.matches({"subject_id": "X:1", "object_id": "ORDO:456"})

    def test_matches_predicate_id(self):
        rule = MappingRule(predicate_id="skos:exactMatch")
        assert rule.matches({"predicate_id": "skos:exactMatch", "subject_id": "X:1"})
        assert not rule.matches({"predicate_id": "skos:broadMatch", "subject_id": "X:1"})

    def test_matches_mapping_justification(self):
        rule = MappingRule(mapping_justification="semapv:LexicalMatching")
        assert rule.matches(
            {"mapping_justification": "semapv:LexicalMatching", "subject_id": "X:1"},
        )
        assert not rule.matches(
            {"mapping_justification": "semapv:ManualMappingCuration", "subject_id": "X:1"},
        )

    def test_matches_multiple_filters(self):
        rule = MappingRule(
            subject_source="OMIM",
            predicate_id="skos:exactMatch",
        )
        assert rule.matches({
            "subject_id": "OMIM:100", "object_id": "MONDO:1",
            "predicate_id": "skos:exactMatch",
        })
        assert not rule.matches({
            "subject_id": "OMIM:100", "object_id": "MONDO:1",
            "predicate_id": "skos:broadMatch",
        })
        assert not rule.matches({
            "subject_id": "ORDO:100", "object_id": "MONDO:1",
            "predicate_id": "skos:exactMatch",
        })

    def test_matches_empty_rule(self):
        """A rule with no filters matches everything."""
        rule = MappingRule()
        assert rule.matches({"subject_id": "X:1", "object_id": "Y:2"})

    def test_skip_flag(self):
        rule = MappingRule(subject_source="OMIM", skip=True)
        assert rule.skip
        assert rule.matches({"subject_id": "OMIM:100"})


class TestSSSOMConverterConfig:
    def test_defaults(self):
        cfg = SSSOMConverterConfig()
        assert cfg.predicate_defaults == DEFAULT_PREDICATE_PROBS
        assert cfg.default_confidence_transform == "identity"
        assert cfg.auto_disjoint_groups is True
        assert cfg.min_probability == 0.01
        assert cfg.rules == []

    def test_custom_config(self):
        cfg = SSSOMConverterConfig(
            min_probability=0.05,
            subject_prefixes=["ORDO", "OMIM"],
            object_prefixes=["MONDO"],
            rules=[MappingRule(subject_source="OMIM", probability=0.5)],
        )
        assert cfg.min_probability == 0.05
        assert cfg.subject_prefixes == ["ORDO", "OMIM"]
        assert len(cfg.rules) == 1

    def test_predicate_defaults_are_independent_copies(self):
        """Mutating one config's defaults must not affect another."""
        cfg1 = SSSOMConverterConfig()
        cfg2 = SSSOMConverterConfig()
        cfg1.predicate_defaults["skos:exactMatch"] = 0.1
        assert cfg2.predicate_defaults["skos:exactMatch"] == 0.9

    def test_yaml_deserialization(self):
        yaml_str = """
predicate_defaults:
  skos:exactMatch: 0.95
default_confidence_transform: rescale
default_transform_params:
  low: 0.1
  high: 0.9
rules:
  - subject_source: OMIM
    probability: 0.6
    skip: false
  - subject_source: BAD
    skip: true
min_probability: 0.05
auto_disjoint_groups: true
"""
        data = yaml.safe_load(yaml_str)
        cfg = SSSOMConverterConfig.model_validate(data)
        assert cfg.predicate_defaults["skos:exactMatch"] == 0.95
        assert cfg.default_confidence_transform == "rescale"
        assert cfg.default_transform_params == {"low": 0.1, "high": 0.9}
        assert len(cfg.rules) == 2
        assert cfg.rules[0].subject_source == "OMIM"
        assert cfg.rules[0].probability == 0.6
        assert cfg.rules[1].skip is True
        assert cfg.min_probability == 0.05


# =========================================================================
# Task 4: Core conversion logic
# =========================================================================


class TestMakeFact:
    def test_exact_match(self):
        f = _make_fact("skos:exactMatch", "A:1", "B:2")
        assert isinstance(f, EquivalentTo)
        assert f.sub == "A:1"
        assert f.equivalent == "B:2"

    def test_close_match(self):
        f = _make_fact("skos:closeMatch", "A:1", "B:2")
        assert isinstance(f, EquivalentTo)

    def test_broad_match(self):
        """broadMatch: A broadMatch B  =>  B subClassOf A"""
        f = _make_fact("skos:broadMatch", "A:1", "B:2")
        assert isinstance(f, ProperSubClassOf)
        assert f.sub == "B:2"
        assert f.sup == "A:1"

    def test_narrow_match(self):
        """narrowMatch: A narrowMatch B  =>  A subClassOf B"""
        f = _make_fact("skos:narrowMatch", "A:1", "B:2")
        assert isinstance(f, ProperSubClassOf)
        assert f.sub == "A:1"
        assert f.sup == "B:2"

    def test_owl_equivalent_class(self):
        f = _make_fact("owl:equivalentClass", "A:1", "B:2")
        assert isinstance(f, EquivalentTo)

    def test_rdfs_subclass_of(self):
        f = _make_fact("rdfs:subClassOf", "A:1", "B:2")
        assert isinstance(f, ProperSubClassOf)
        assert f.sub == "A:1"
        assert f.sup == "B:2"

    def test_unknown_predicate(self):
        assert _make_fact("skos:relatedMatch", "A:1", "B:2") is None


class TestSssomMappingsToPfacts:
    def test_basic_conversion(self):
        rows = [
            {
                "subject_id": "A:1", "object_id": "B:2",
                "predicate_id": "skos:exactMatch", "confidence": "0.85",
            },
        ]
        pfacts = sssom_mappings_to_pfacts(rows)
        assert len(pfacts) == 1
        assert pfacts[0].prob == 0.85
        assert isinstance(pfacts[0].fact, EquivalentTo)
        assert pfacts[0].fact.sub == "A:1"
        assert pfacts[0].fact.equivalent == "B:2"

    def test_no_confidence_falls_back_to_predicate_default(self):
        rows = [
            {
                "subject_id": "A:1", "object_id": "B:2",
                "predicate_id": "skos:exactMatch",
            },
        ]
        pfacts = sssom_mappings_to_pfacts(rows)
        assert len(pfacts) == 1
        assert pfacts[0].prob == DEFAULT_PREDICATE_PROBS["skos:exactMatch"]

    def test_empty_confidence_falls_back(self):
        rows = [
            {
                "subject_id": "A:1", "object_id": "B:2",
                "predicate_id": "skos:exactMatch", "confidence": "",
            },
        ]
        pfacts = sssom_mappings_to_pfacts(rows)
        assert len(pfacts) == 1
        assert pfacts[0].prob == 0.9

    def test_rule_probability_override(self):
        rows = [
            {
                "subject_id": "OMIM:100", "object_id": "MONDO:1",
                "predicate_id": "skos:exactMatch", "confidence": "0.85",
            },
        ]
        cfg = SSSOMConverterConfig(
            rules=[MappingRule(subject_source="OMIM", probability=0.6)],
        )
        pfacts = sssom_mappings_to_pfacts(rows, cfg)
        assert len(pfacts) == 1
        assert pfacts[0].prob == 0.6

    def test_rule_skip(self):
        rows = [
            {
                "subject_id": "OMIM:100", "object_id": "MONDO:1",
                "predicate_id": "skos:exactMatch", "confidence": "0.85",
            },
            {
                "subject_id": "ORDO:200", "object_id": "MONDO:2",
                "predicate_id": "skos:exactMatch", "confidence": "0.9",
            },
        ]
        cfg = SSSOMConverterConfig(
            rules=[MappingRule(subject_source="OMIM", skip=True)],
        )
        pfacts = sssom_mappings_to_pfacts(rows, cfg)
        assert len(pfacts) == 1
        assert pfacts[0].fact.sub == "ORDO:200"

    def test_confidence_transform_applied(self):
        rows = [
            {
                "subject_id": "A:1", "object_id": "B:2",
                "predicate_id": "skos:exactMatch", "confidence": "0.5",
            },
        ]
        cfg = SSSOMConverterConfig(
            default_confidence_transform="rescale",
            default_transform_params={"low": 0.2, "high": 0.8},
        )
        pfacts = sssom_mappings_to_pfacts(rows, cfg)
        assert len(pfacts) == 1
        # rescale(0.5) = 0.2 + 0.5 * (0.8 - 0.2) = 0.5
        assert pfacts[0].prob == pytest.approx(0.5)

    def test_rule_specific_transform(self):
        rows = [
            {
                "subject_id": "OMIM:100", "object_id": "MONDO:1",
                "predicate_id": "skos:exactMatch", "confidence": "0.5",
            },
        ]
        cfg = SSSOMConverterConfig(
            rules=[
                MappingRule(
                    subject_source="OMIM",
                    confidence_transform="rescale",
                    transform_params={"low": 0.3, "high": 0.7},
                ),
            ],
        )
        pfacts = sssom_mappings_to_pfacts(rows, cfg)
        assert len(pfacts) == 1
        # rescale(0.5) = 0.3 + 0.5 * (0.7 - 0.3) = 0.5
        assert pfacts[0].prob == pytest.approx(0.5)

    def test_prefix_filters_subject(self):
        rows = [
            {"subject_id": "ORDO:1", "object_id": "MONDO:1", "predicate_id": "skos:exactMatch", "confidence": "0.9"},
            {"subject_id": "OMIM:1", "object_id": "MONDO:1", "predicate_id": "skos:exactMatch", "confidence": "0.9"},
        ]
        cfg = SSSOMConverterConfig(subject_prefixes=["ORDO"])
        pfacts = sssom_mappings_to_pfacts(rows, cfg)
        assert len(pfacts) == 1
        assert pfacts[0].fact.sub == "ORDO:1"

    def test_prefix_filters_object(self):
        rows = [
            {"subject_id": "ORDO:1", "object_id": "MONDO:1", "predicate_id": "skos:exactMatch", "confidence": "0.9"},
            {"subject_id": "ORDO:2", "object_id": "HP:1", "predicate_id": "skos:exactMatch", "confidence": "0.9"},
        ]
        cfg = SSSOMConverterConfig(object_prefixes=["MONDO"])
        pfacts = sssom_mappings_to_pfacts(rows, cfg)
        assert len(pfacts) == 1
        assert pfacts[0].fact.equivalent == "MONDO:1"

    def test_min_probability_filtering(self):
        rows = [
            {"subject_id": "A:1", "object_id": "B:2", "predicate_id": "skos:exactMatch", "confidence": "0.005"},
            {"subject_id": "A:3", "object_id": "B:4", "predicate_id": "skos:exactMatch", "confidence": "0.5"},
        ]
        cfg = SSSOMConverterConfig(min_probability=0.01)
        pfacts = sssom_mappings_to_pfacts(rows, cfg)
        assert len(pfacts) == 1
        assert pfacts[0].prob == 0.5

    def test_unknown_predicate_skipped(self):
        rows = [
            {"subject_id": "A:1", "object_id": "B:2", "predicate_id": "skos:relatedMatch", "confidence": "0.9"},
        ]
        pfacts = sssom_mappings_to_pfacts(rows)
        assert len(pfacts) == 0

    def test_broad_match_reversal(self):
        rows = [
            {
                "subject_id": "A:1", "object_id": "B:2",
                "predicate_id": "skos:broadMatch", "confidence": "0.8",
            },
        ]
        pfacts = sssom_mappings_to_pfacts(rows)
        assert len(pfacts) == 1
        f = pfacts[0].fact
        assert isinstance(f, ProperSubClassOf)
        assert f.sub == "B:2"
        assert f.sup == "A:1"

    def test_narrow_match_direction(self):
        rows = [
            {
                "subject_id": "A:1", "object_id": "B:2",
                "predicate_id": "skos:narrowMatch", "confidence": "0.8",
            },
        ]
        pfacts = sssom_mappings_to_pfacts(rows)
        assert len(pfacts) == 1
        f = pfacts[0].fact
        assert isinstance(f, ProperSubClassOf)
        assert f.sub == "A:1"
        assert f.sup == "B:2"


class TestSssomToKb:
    def test_basic_conversion(self):
        kb = sssom_to_kb(SSSOM_FILE)
        assert isinstance(kb, KB)
        assert kb.name == "https://example.org/test_mappings"
        assert kb.description == "Test mappings for boomer SSSOM converter"

    def test_pfacts_count_and_types(self):
        kb = sssom_to_kb(SSSOM_FILE)
        # 5 rows in fixture, all have known predicates
        assert len(kb.pfacts) == 5

        equiv_pfacts = [pf for pf in kb.pfacts if isinstance(pf.fact, EquivalentTo)]
        sub_pfacts = [pf for pf in kb.pfacts if isinstance(pf.fact, ProperSubClassOf)]
        # exactMatch rows: 3 (rows 1, 3, 4) => EquivalentTo
        assert len(equiv_pfacts) == 3
        # broadMatch row: 1 (row 2), narrowMatch row: 1 (row 5) => ProperSubClassOf
        assert len(sub_pfacts) == 2

    def test_probabilities(self):
        kb = sssom_to_kb(SSSOM_FILE)
        prob_map = {
            (type(pf.fact).__name__, _fact_key(pf.fact)): pf.prob
            for pf in kb.pfacts
        }
        # Row 1: ORDO:123 exactMatch MONDO:0001234 conf=0.95
        assert prob_map[("EquivalentTo", ("ORDO:123", "MONDO:0001234"))] == 0.95
        # Row 3: ORDO:789 exactMatch MONDO:0005678 conf=0.99
        assert prob_map[("EquivalentTo", ("ORDO:789", "MONDO:0005678"))] == 0.99

    def test_labels_extracted(self):
        kb = sssom_to_kb(SSSOM_FILE)
        assert kb.labels["ORDO:123"] == "Alpha disease"
        assert kb.labels["MONDO:0001234"] == "Alpha disorder"
        assert kb.labels["ORDO:789"] == "Gamma disease"
        assert kb.labels["MONDO:0005678"] == "Gamma disorder"
        assert kb.labels["OMIM:100100"] == "Delta syndrome"
        assert kb.labels["ORDO:456"] == "Beta disease"

    def test_disjoint_groups(self):
        kb = sssom_to_kb(SSSOM_FILE)
        groups = {(f.sub, f.group) for f in kb.facts if isinstance(f, MemberOfDisjointGroup)}
        # Check that entities get their prefix as group
        assert ("ORDO:123", "ORDO") in groups
        assert ("MONDO:0001234", "MONDO") in groups
        assert ("OMIM:100100", "OMIM") in groups

    def test_disjoint_groups_disabled(self):
        cfg = SSSOMConverterConfig(auto_disjoint_groups=False)
        kb = sssom_to_kb(SSSOM_FILE, cfg)
        assert len(kb.facts) == 0

    def test_with_rules(self):
        cfg = SSSOMConverterConfig(
            rules=[MappingRule(subject_source="OMIM", probability=0.5)],
        )
        kb = sssom_to_kb(SSSOM_FILE, cfg)
        # The OMIM row should have probability overridden
        omim_pfacts = [
            pf for pf in kb.pfacts
            if isinstance(pf.fact, EquivalentTo) and pf.fact.sub == "OMIM:100100"
        ]
        assert len(omim_pfacts) == 1
        assert omim_pfacts[0].prob == 0.5

    def test_with_skip_rule(self):
        cfg = SSSOMConverterConfig(
            rules=[MappingRule(subject_source="OMIM", skip=True)],
        )
        kb = sssom_to_kb(SSSOM_FILE, cfg)
        omim_pfacts = [
            pf for pf in kb.pfacts
            if isinstance(pf.fact, EquivalentTo) and pf.fact.sub == "OMIM:100100"
        ]
        assert len(omim_pfacts) == 0

    def test_with_confidence_transform(self):
        cfg = SSSOMConverterConfig(
            default_confidence_transform="floor_ceil",
            default_transform_params={"floor": 0.1, "ceil": 0.9},
        )
        kb = sssom_to_kb(SSSOM_FILE, cfg)
        # Row 3: conf=0.99, clamped to 0.9
        row3_pfacts = [
            pf for pf in kb.pfacts
            if isinstance(pf.fact, EquivalentTo)
            and pf.fact.sub == "ORDO:789"
            and pf.fact.equivalent == "MONDO:0005678"
        ]
        assert len(row3_pfacts) == 1
        assert row3_pfacts[0].prob == pytest.approx(0.9)

    def test_with_prefix_filters(self):
        cfg = SSSOMConverterConfig(
            subject_prefixes=["ORDO"],
            object_prefixes=["MONDO"],
        )
        kb = sssom_to_kb(SSSOM_FILE, cfg)
        # Only ORDO subjects should remain (rows 1, 2, 3, 5)
        # OMIM:100100 subject (row 4) should be filtered out
        omim_pfacts = [
            pf for pf in kb.pfacts
            if _has_entity(pf.fact, "OMIM:100100")
        ]
        assert len(omim_pfacts) == 0

    def test_min_probability_filtering(self):
        cfg = SSSOMConverterConfig(min_probability=0.5)
        kb = sssom_to_kb(SSSOM_FILE, cfg)
        # Row 5 has confidence=0.4, should be filtered
        for pf in kb.pfacts:
            assert pf.prob >= 0.5

    def test_no_confidence_column(self):
        """When no confidence column exists, fall back to predicate defaults."""
        content = (
            "#mapping_set_id: https://example.org/noconf\n"
            "subject_id\tobject_id\tpredicate_id\n"
            "A:1\tB:2\tskos:exactMatch\n"
            "A:3\tB:4\tskos:broadMatch\n"
        )
        path = _write_sssom(content)
        kb = sssom_to_kb(path)
        assert len(kb.pfacts) == 2
        probs = {pf.prob for pf in kb.pfacts}
        assert 0.9 in probs  # exactMatch default
        assert 0.7 in probs  # broadMatch default
        os.unlink(path)

    def test_broad_match_direction_in_kb(self):
        """broadMatch should produce reversed ProperSubClassOf."""
        kb = sssom_to_kb(SSSOM_FILE)
        broad_pfacts = [
            pf for pf in kb.pfacts
            if isinstance(pf.fact, ProperSubClassOf)
            and pf.fact.sup == "ORDO:456"
        ]
        # Row 2: ORDO:456 broadMatch MONDO:0001234
        # => ProperSubClassOf(sub=MONDO:0001234, sup=ORDO:456)
        assert len(broad_pfacts) == 1
        assert broad_pfacts[0].fact.sub == "MONDO:0001234"

    def test_narrow_match_direction_in_kb(self):
        """narrowMatch should produce non-reversed ProperSubClassOf."""
        kb = sssom_to_kb(SSSOM_FILE)
        narrow_pfacts = [
            pf for pf in kb.pfacts
            if isinstance(pf.fact, ProperSubClassOf)
            and pf.fact.sub == "ORDO:123"
            and pf.fact.sup == "MONDO:0005678"
        ]
        # Row 5: ORDO:123 narrowMatch MONDO:0005678
        # => ProperSubClassOf(sub=ORDO:123, sup=MONDO:0005678)
        assert len(narrow_pfacts) == 1
        assert narrow_pfacts[0].prob == 0.4

    def test_ids_without_colons(self):
        """IDs without colons should not crash disjoint group generation."""
        content = (
            "subject_id\tobject_id\tpredicate_id\tconfidence\n"
            "bare_id\tB:2\tskos:exactMatch\t0.9\n"
        )
        path = _write_sssom(content)
        kb = sssom_to_kb(path)
        # bare_id has no colon, should be skipped for disjoint groups
        disjoint_subs = {f.sub for f in kb.facts if isinstance(f, MemberOfDisjointGroup)}
        assert "bare_id" not in disjoint_subs
        assert "B:2" in disjoint_subs
        assert len(kb.pfacts) == 1
        os.unlink(path)


# =========================================================================
# Task 5: Config file loading and integration
# =========================================================================

SSSOM_CONFIG_FILE = Path(__file__).parent / "input" / "sssom_config.yaml"


class TestLoadSssomConfig:
    def test_load_from_file(self):
        config = load_sssom_config(SSSOM_CONFIG_FILE)
        assert config.predicate_defaults["skos:exactMatch"] == 0.85
        assert config.default_confidence_transform == "floor_ceil"
        assert len(config.rules) == 2
        assert config.rules[0].subject_source == "OMIM"
        assert config.rules[0].probability == 0.95
        assert config.rules[1].mapping_justification == "semapv:LexicalMatching"
        assert config.min_probability == 0.05

    def test_full_pipeline_with_config_file(self):
        """SSSOM file + config file -> KB with correct probability overrides."""
        config = load_sssom_config(SSSOM_CONFIG_FILE)
        kb = sssom_to_kb(SSSOM_FILE, config=config)

        # OMIM row: rule 1 applies (subject_source=OMIM), hard override prob=0.95
        omim_pfacts = [p for p in kb.pfacts if isinstance(p.fact, EquivalentTo)
                       and p.fact.sub == "OMIM:100100"]
        assert len(omim_pfacts) == 1
        assert omim_pfacts[0].prob == pytest.approx(0.95)

        # ORDO:123 exactMatch MONDO:0001234: confidence=0.95, justification=LexicalMatching
        # Rule 2 matches (LexicalMatching): rescale(0.95, low=0.2, high=0.7)
        # = 0.2 + 0.95 * 0.5 = 0.675
        ordo_exact = [p for p in kb.pfacts if isinstance(p.fact, EquivalentTo)
                      and p.fact.sub == "ORDO:123" and p.fact.equivalent == "MONDO:0001234"]
        assert len(ordo_exact) == 1
        assert ordo_exact[0].prob == pytest.approx(0.675)

        # ORDO:789 exactMatch MONDO:0005678: confidence=0.99, justification=ManualMappingCuration
        # No rule matches -> default transform: floor_ceil(0.99, floor=0.05, ceil=0.95) = 0.95
        manual_exact = [p for p in kb.pfacts if isinstance(p.fact, EquivalentTo)
                        and p.fact.sub == "ORDO:789"]
        assert len(manual_exact) == 1
        assert manual_exact[0].prob == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _fact_key(fact):
    """Return a tuple key for a fact for easy lookup."""
    if isinstance(fact, EquivalentTo):
        return (fact.sub, fact.equivalent)
    if isinstance(fact, ProperSubClassOf):
        return (fact.sub, fact.sup)
    return ()


def _has_entity(fact, entity_id: str) -> bool:
    """Check whether a fact mentions *entity_id* in any position."""
    if isinstance(fact, EquivalentTo):
        return fact.sub == entity_id or fact.equivalent == entity_id
    if isinstance(fact, ProperSubClassOf):
        return fact.sub == entity_id or fact.sup == entity_id
    return False
