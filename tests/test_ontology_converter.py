"""Tests for boomer.ontology_converter."""

from pathlib import Path

import pytest

from boomer.ontology_converter import (
    OntologyConverterConfig,
    _has_pyhornedowl,
    _strip_comment,
    _strip_qualifiers,
    load_ontology_config,
    obo_to_kb,
    ontology_to_kb,
    parse_obo,
)

OBO_FIXTURE = Path("tests/input/test_ontology.obo")
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
# Dispatch tests
# ---------------------------------------------------------------------------


class TestOntologyToKb:
    def test_dispatch_obo(self):
        kb = ontology_to_kb(OBO_FIXTURE)
        assert kb.name == "test-ontology"

    def test_dispatch_unknown(self):
        with pytest.raises(ValueError, match="Unrecognized ontology extension"):
            ontology_to_kb("foo.xyz")


# ---------------------------------------------------------------------------
# OWL backend tests (skipped if py-horned-owl not installed)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _has_pyhornedowl(),
    reason="py-horned-owl not installed",
)
class TestOwlToKb:
    pass  # OWL tests would go here when OWL fixtures are available
