"""Tests for boomer.ontology_converter."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from boomer.cli import cli
from boomer.loaders import KBLoader, load_kb_smart
from boomer.ontology_converter import (
    OntologyConverterConfig,
    _strip_comment,
    _strip_qualifiers,
    load_ontology_config,
    obo_to_kb,
    ontology_to_kb,
    owl_to_kb,
    parse_obo,
)

OBO_FIXTURE = Path("tests/input/test_ontology.obo")
OFN_FIXTURE = Path("tests/input/test_ontology.ofn")
SSSOM_FIXTURE = Path("tests/input/test_mappings.sssom.tsv")
CONFIG_FIXTURE = Path("tests/input/ontology_config.yaml")


# ---------------------------------------------------------------------------
# OBO parser tests
# ---------------------------------------------------------------------------


class TestParseOBO:
    @pytest.fixture()
    def doc(self):
        return parse_obo(OBO_FIXTURE)

    def test_header_ontology(self, doc):
        assert doc.ontology == "test-ontology"

    def test_term_count(self, doc):
        assert len(doc.terms) == 5

    def test_term_ids(self, doc):
        ids = [t.id for t in doc.terms]
        assert ids == ["TEST:0001", "TEST:0002", "TEST:0003", "TEST:0004", "TEST:0005"]

    def test_is_a(self, doc):
        t2 = doc.terms[1]
        assert t2.id == "TEST:0002"
        assert t2.is_a == ["TEST:0001"]

    def test_xref(self, doc):
        t1 = doc.terms[0]
        assert t1.id == "TEST:0001"
        assert t1.xrefs == ["EXT:R001"]

    def test_skos_property_values(self, doc):
        t2 = doc.terms[1]
        assert ("skos:exactMatch", "EXT:C001A") in t2.skos_mappings
        assert ("skos:broadMatch", "EXT:BROAD1") in t2.skos_mappings

    def test_equivalent_to(self, doc):
        t3 = doc.terms[2]
        assert t3.equivalent_to == ["EXT:EQ001"]

    def test_disjoint_from(self, doc):
        t3 = doc.terms[2]
        assert t3.disjoint_from == ["TEST:0002"]

    def test_is_obsolete(self, doc):
        t5 = doc.terms[4]
        assert t5.is_obsolete is True

    def test_typedef_skipped(self, doc):
        ids = {t.id for t in doc.terms}
        assert "TEST:R001" not in ids

    def test_name(self, doc):
        assert doc.terms[0].name == "Root class"

    def test_comment_stripping(self):
        assert _strip_comment("TEST:0001 ! Root class") == "TEST:0001"
        assert _strip_comment("TEST:0001") == "TEST:0001"

    def test_qualifier_stripping(self):
        assert _strip_qualifiers('EXT:R001 {source="manual"}') == "EXT:R001"
        assert _strip_qualifiers("EXT:R001") == "EXT:R001"


# ---------------------------------------------------------------------------
# OBO → KB conversion tests
# ---------------------------------------------------------------------------


class TestOboToKb:
    @pytest.fixture()
    def kb(self):
        return obo_to_kb(OBO_FIXTURE)

    @pytest.fixture()
    def custom_kb(self):
        config = OntologyConverterConfig(
            xref_prefix_probabilities={"EXT": 0.85},
        )
        return obo_to_kb(OBO_FIXTURE, config)

    def test_basic_conversion(self, kb):
        assert kb is not None

    def test_is_a_hard_facts(self, kb):
        subclass_facts = [
            f for f in kb.facts if hasattr(f, "sup") and f.fact_type == "ProperSubClassOf"
        ]
        # TEST:0002 is_a TEST:0001 and TEST:0003 is_a TEST:0001
        # (TEST:0005 is obsolete, skipped by default)
        assert len(subclass_facts) == 2

    def test_equivalent_to_hard_facts(self, kb):
        equiv_facts = [
            f for f in kb.facts if f.fact_type == "EquivalentTo"
        ]
        assert len(equiv_facts) == 1
        assert equiv_facts[0].sub == "TEST:0003"
        assert equiv_facts[0].equivalent == "EXT:EQ001"

    def test_disjoint_from_hard_facts(self, kb):
        disj_facts = [
            f for f in kb.facts if f.fact_type == "DisjointWith"
        ]
        assert len(disj_facts) == 1
        assert disj_facts[0].sub == "TEST:0003"
        assert disj_facts[0].sibling == "TEST:0002"

    def test_xref_pfacts(self, kb):
        xref_pfacts = [
            p for p in kb.pfacts
            if p.fact.fact_type == "EquivalentTo"
            and p.fact.equivalent in ("EXT:R001", "EXT:C001")
        ]
        # TEST:0001 xref EXT:R001, TEST:0002 xref EXT:C001
        assert len(xref_pfacts) == 2

    def test_xref_default_probability(self, kb):
        xref_pfact = next(
            p for p in kb.pfacts
            if p.fact.fact_type == "EquivalentTo" and p.fact.equivalent == "EXT:R001"
        )
        assert xref_pfact.prob == 0.7

    def test_xref_prefix_override(self, custom_kb):
        xref_pfact = next(
            p for p in custom_kb.pfacts
            if p.fact.fact_type == "EquivalentTo" and p.fact.equivalent == "EXT:R001"
        )
        assert xref_pfact.prob == 0.85

    def test_skos_exact_match(self, kb):
        exact = next(
            p for p in kb.pfacts
            if p.fact.fact_type == "EquivalentTo" and p.fact.equivalent == "EXT:C001A"
        )
        assert exact.prob == 0.9

    def test_skos_broad_match_reversed(self, kb):
        # broadMatch: "TEST:0002 broadMatch EXT:BROAD1"
        # means EXT:BROAD1 subClassOf TEST:0002 (broad is the subject)
        broad = next(
            p for p in kb.pfacts
            if p.fact.fact_type == "ProperSubClassOf"
            and p.fact.sup == "TEST:0002"
            and p.fact.sub == "EXT:BROAD1"
        )
        assert broad.prob == 0.7

    def test_skos_narrow_match(self, kb):
        # narrowMatch: "TEST:0004 narrowMatch EXT:NARROW1"
        # means TEST:0004 subClassOf EXT:NARROW1
        narrow = next(
            p for p in kb.pfacts
            if p.fact.fact_type == "ProperSubClassOf"
            and p.fact.sub == "TEST:0004"
            and p.fact.sup == "EXT:NARROW1"
        )
        assert narrow.prob == 0.7

    def test_skos_close_match(self, kb):
        close = next(
            p for p in kb.pfacts
            if p.fact.fact_type == "EquivalentTo" and p.fact.equivalent == "EXT:CLOSE1"
        )
        assert close.prob == 0.7

    def test_obsolete_skipped(self, kb):
        all_subs = [
            f.sub for f in kb.facts if hasattr(f, "sup") and f.fact_type == "ProperSubClassOf"
        ]
        assert "TEST:0005" not in all_subs

    def test_obsolete_included(self):
        config = OntologyConverterConfig(skip_obsolete=False)
        kb = obo_to_kb(OBO_FIXTURE, config)
        subclass_facts = [
            f for f in kb.facts if hasattr(f, "sup") and f.fact_type == "ProperSubClassOf"
        ]
        # Now includes TEST:0005 is_a TEST:0001
        assert len(subclass_facts) == 3

    def test_labels(self, kb):
        assert kb.labels["TEST:0001"] == "Root class"
        assert kb.labels["TEST:0002"] == "Child class A"

    def test_disjoint_groups(self, kb):
        disjoint_groups = [
            f for f in kb.facts if f.fact_type == "MemberOfDisjointGroup"
        ]
        assert len(disjoint_groups) > 0
        prefixes = {f.group for f in disjoint_groups}
        assert "TEST" in prefixes
        assert "EXT" in prefixes

    def test_disjoint_groups_disabled(self):
        config = OntologyConverterConfig(auto_disjoint_groups=False)
        kb = obo_to_kb(OBO_FIXTURE, config)
        disjoint_groups = [
            f for f in kb.facts if f.fact_type == "MemberOfDisjointGroup"
        ]
        assert len(disjoint_groups) == 0

    def test_include_xrefs_false(self):
        config = OntologyConverterConfig(include_xrefs=False)
        kb = obo_to_kb(OBO_FIXTURE, config)
        xref_pfacts = [
            p for p in kb.pfacts
            if p.fact.fact_type == "EquivalentTo"
            and p.fact.equivalent in ("EXT:R001", "EXT:C001")
        ]
        assert len(xref_pfacts) == 0

    def test_include_skos_false(self):
        config = OntologyConverterConfig(include_skos=False)
        kb = obo_to_kb(OBO_FIXTURE, config)
        skos_pfacts = [
            p for p in kb.pfacts
            if p.fact.fact_type in ("EquivalentTo", "ProperSubClassOf")
            and any(
                t in str(p.fact)
                for t in ("C001A", "BROAD1", "NARROW1", "CLOSE1")
            )
        ]
        assert len(skos_pfacts) == 0

    def test_min_probability_filter(self):
        config = OntologyConverterConfig(
            xref_default_probability=0.005,
            min_probability=0.01,
        )
        kb = obo_to_kb(OBO_FIXTURE, config)
        xref_pfacts = [
            p for p in kb.pfacts
            if p.fact.fact_type == "EquivalentTo"
            and p.fact.equivalent in ("EXT:R001", "EXT:C001")
        ]
        assert len(xref_pfacts) == 0

    def test_kb_name(self, kb):
        assert kb.name == "test-ontology"

    def test_config_from_file(self):
        config = load_ontology_config(CONFIG_FIXTURE)
        kb = obo_to_kb(OBO_FIXTURE, config)
        assert kb is not None
        # Config sets xref_default_probability to 0.8
        xref_pfact = next(
            p for p in kb.pfacts
            if p.fact.fact_type == "EquivalentTo" and p.fact.equivalent == "EXT:R001"
        )
        assert xref_pfact.prob == 0.8


# ---------------------------------------------------------------------------
# OWL → KB conversion tests
# ---------------------------------------------------------------------------


class TestOwlToKb:
    @pytest.fixture()
    def kb(self):
        return owl_to_kb(OFN_FIXTURE)

    def test_basic_conversion(self, kb):
        assert kb is not None

    def test_kb_name(self, kb):
        assert kb.name == "http://example.org/test-ontology"

    def test_labels(self, kb):
        assert kb.labels["TEST:0001"] == "Root class"
        assert kb.labels["TEST:0002"] == "Child class A"
        assert kb.labels["TEST:0003"] == "Child class B"
        assert kb.labels["TEST:0004"] == "Narrow mapped class"

    def test_subclass_hard_facts(self, kb):
        subclass_facts = [
            f for f in kb.facts if f.fact_type == "ProperSubClassOf"
        ]
        subs = {(f.sub, f.sup) for f in subclass_facts}
        assert ("TEST:0002", "TEST:0001") in subs
        assert ("TEST:0003", "TEST:0001") in subs
        assert len(subclass_facts) == 2

    def test_equivalent_hard_facts(self, kb):
        equiv_facts = [
            f for f in kb.facts if f.fact_type == "EquivalentTo"
        ]
        assert len(equiv_facts) == 1
        assert equiv_facts[0].sub == "TEST:0003"
        assert equiv_facts[0].equivalent == "EXT:EQ001"

    def test_disjoint_hard_facts(self, kb):
        disj_facts = [
            f for f in kb.facts if f.fact_type == "DisjointWith"
        ]
        assert len(disj_facts) == 1
        pair = {disj_facts[0].sub, disj_facts[0].sibling}
        assert pair == {"TEST:0002", "TEST:0003"}

    def test_xref_pfacts(self, kb):
        xref_pfacts = [
            p for p in kb.pfacts
            if p.fact.fact_type == "EquivalentTo"
            and p.fact.equivalent in ("EXT:R001", "EXT:C001")
        ]
        assert len(xref_pfacts) == 2
        for p in xref_pfacts:
            assert p.prob == 0.7

    def test_skos_exact_match(self, kb):
        exact = next(
            p for p in kb.pfacts
            if p.fact.fact_type == "EquivalentTo" and p.fact.equivalent == "EXT:C001A"
        )
        assert exact.prob == 0.9

    def test_skos_broad_match_reversed(self, kb):
        broad = next(
            p for p in kb.pfacts
            if p.fact.fact_type == "ProperSubClassOf"
            and p.fact.sup == "TEST:0002"
            and p.fact.sub == "EXT:BROAD1"
        )
        assert broad.prob == 0.7

    def test_skos_narrow_match(self, kb):
        narrow = next(
            p for p in kb.pfacts
            if p.fact.fact_type == "ProperSubClassOf"
            and p.fact.sub == "TEST:0004"
            and p.fact.sup == "EXT:NARROW1"
        )
        assert narrow.prob == 0.7

    def test_skos_close_match(self, kb):
        close = next(
            p for p in kb.pfacts
            if p.fact.fact_type == "EquivalentTo" and p.fact.equivalent == "EXT:CLOSE1"
        )
        assert close.prob == 0.7

    def test_disjoint_groups(self, kb):
        disjoint_groups = [
            f for f in kb.facts if f.fact_type == "MemberOfDisjointGroup"
        ]
        prefixes = {f.group for f in disjoint_groups}
        assert "TEST" in prefixes
        assert "EXT" in prefixes

    def test_obo_iri_conversion(self):
        """OBO-style IRIs like http://purl.obolibrary.org/obo/GO_0008150 → GO:0008150."""
        from boomer.ontology_converter import _iri_to_curie
        assert _iri_to_curie("http://purl.obolibrary.org/obo/GO_0008150") == "GO:0008150"
        assert _iri_to_curie("http://purl.obolibrary.org/obo/MONDO_0001234") == "MONDO:0001234"


# ---------------------------------------------------------------------------
# OBO vs OWL parity: both fixtures should produce equivalent KB structure
# ---------------------------------------------------------------------------


class TestOboOwlParity:
    """Verify that OBO and OWL converters produce structurally equivalent KBs."""

    @pytest.fixture()
    def obo_kb(self):
        return obo_to_kb(OBO_FIXTURE)

    @pytest.fixture()
    def owl_kb(self):
        return owl_to_kb(OFN_FIXTURE)

    def test_same_subclass_count(self, obo_kb, owl_kb):
        obo_sc = [f for f in obo_kb.facts if f.fact_type == "ProperSubClassOf"]
        owl_sc = [f for f in owl_kb.facts if f.fact_type == "ProperSubClassOf"]
        assert len(obo_sc) == len(owl_sc)

    def test_same_equivalence_count(self, obo_kb, owl_kb):
        obo_eq = [f for f in obo_kb.facts if f.fact_type == "EquivalentTo"]
        owl_eq = [f for f in owl_kb.facts if f.fact_type == "EquivalentTo"]
        assert len(obo_eq) == len(owl_eq)

    def test_same_disjoint_count(self, obo_kb, owl_kb):
        obo_dj = [f for f in obo_kb.facts if f.fact_type == "DisjointWith"]
        owl_dj = [f for f in owl_kb.facts if f.fact_type == "DisjointWith"]
        assert len(obo_dj) == len(owl_dj)

    def test_same_xref_pfact_count(self, obo_kb, owl_kb):
        def xref_pfacts(kb):
            return [
                p for p in kb.pfacts
                if p.fact.fact_type == "EquivalentTo"
                and p.fact.equivalent in ("EXT:R001", "EXT:C001")
            ]
        assert len(xref_pfacts(obo_kb)) == len(xref_pfacts(owl_kb))

    def test_same_skos_pfact_count(self, obo_kb, owl_kb):
        def skos_pfacts(kb):
            return [
                p for p in kb.pfacts
                if any(t in str(p.fact) for t in ("C001A", "BROAD1", "NARROW1", "CLOSE1"))
            ]
        assert len(skos_pfacts(obo_kb)) == len(skos_pfacts(owl_kb))

    def test_same_label_keys(self, obo_kb, owl_kb):
        # OBO has 4 labels (excluding obsolete), OWL also has 4
        assert set(obo_kb.labels.keys()) == set(owl_kb.labels.keys())


# ---------------------------------------------------------------------------
# Dispatch tests
# ---------------------------------------------------------------------------


class TestOntologyToKb:
    def test_dispatch_obo(self):
        kb = ontology_to_kb(OBO_FIXTURE)
        assert kb.name == "test-ontology"

    def test_dispatch_ofn(self):
        kb = ontology_to_kb(OFN_FIXTURE)
        assert kb.name == "http://example.org/test-ontology"

    def test_dispatch_unknown(self):
        with pytest.raises(ValueError, match="Unrecognized ontology extension"):
            ontology_to_kb("foo.xyz")


# ---------------------------------------------------------------------------
# Loader integration tests
# ---------------------------------------------------------------------------


class TestLoaderIntegration:
    def test_detect_format_obo(self):
        assert KBLoader.detect_format("test.obo") == "obo"

    def test_detect_format_owl(self):
        assert KBLoader.detect_format("test.owl") == "owl"
        assert KBLoader.detect_format("test.owx") == "owl"
        assert KBLoader.detect_format("test.ofn") == "owl"

    def test_load_kb_smart_obo(self):
        kb = load_kb_smart(OBO_FIXTURE)
        assert kb.name == "test-ontology"
        assert len(kb.pfacts) > 0

    def test_load_kb_smart_ofn(self):
        kb = load_kb_smart(OFN_FIXTURE)
        assert "test-ontology" in kb.name
        assert len(kb.pfacts) > 0

    def test_load_kb_explicit_format(self):
        kb = load_kb_smart(OBO_FIXTURE, format_name="obo")
        assert kb.name == "test-ontology"


# ---------------------------------------------------------------------------
# CLI integration tests: convert all three formats (OBO, OWL, SSSOM)
# ---------------------------------------------------------------------------


class TestCLIConvert:
    """Test CLI convert command with OBO, OWL, and SSSOM inputs."""

    @pytest.mark.parametrize("input_file,expected_name", [
        (OBO_FIXTURE, "test-ontology"),
        (OFN_FIXTURE, "http://example.org/test-ontology"),
        (SSSOM_FIXTURE, "https://example.org/test_mappings"),
    ])
    def test_convert_to_yaml(self, tmp_path, input_file, expected_name):
        out = tmp_path / "out.yaml"
        runner = CliRunner()
        result = runner.invoke(cli, [
            "convert", str(input_file), "-o", str(out),
        ])
        assert result.exit_code == 0, result.output
        assert out.exists()
        kb = load_kb_smart(str(out), format_name="yaml")
        assert kb.name == expected_name

    @pytest.mark.parametrize("input_file", [
        OBO_FIXTURE,
        OFN_FIXTURE,
        SSSOM_FIXTURE,
    ])
    def test_convert_to_json(self, tmp_path, input_file):
        out = tmp_path / "out.json"
        runner = CliRunner()
        result = runner.invoke(cli, [
            "convert", str(input_file), "-o", str(out),
        ])
        assert result.exit_code == 0, result.output
        assert out.exists()
        kb = load_kb_smart(str(out), format_name="json")
        assert kb is not None
        assert len(kb.pfacts) > 0

    @pytest.mark.parametrize("input_file", [
        OBO_FIXTURE,
        OFN_FIXTURE,
    ])
    def test_convert_roundtrip(self, tmp_path, input_file):
        """Convert to YAML, then load back and verify structure."""
        out = tmp_path / "out.yaml"
        runner = CliRunner()
        result = runner.invoke(cli, [
            "convert", str(input_file), "-o", str(out),
        ])
        assert result.exit_code == 0, result.output
        kb = load_kb_smart(str(out), format_name="yaml")
        # Should have structural facts
        structural = [
            f for f in kb.facts
            if f.fact_type in ("ProperSubClassOf", "EquivalentTo", "DisjointWith")
        ]
        assert len(structural) > 0
        # Should have pfacts from xrefs/SKOS
        assert len(kb.pfacts) > 0
