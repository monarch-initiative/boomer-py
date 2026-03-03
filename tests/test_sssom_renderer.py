"""Tests for the SSSOM TSV solution renderer."""

import pytest
from click.testing import CliRunner

from boomer.model import (
    DisjointWith,
    EquivalentTo,
    KB,
    PFact,
    ProperSubClassOf,
    SearchConfig,
    Solution,
    SolvedPFact,
)
from boomer.renderers.sssom_renderer import (
    SSSOM_COLUMNS,
    SSSOMRenderer,
    fact_to_sssom_row,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spfact(fact, prob=0.9, posterior=0.95, truth_value=True):
    return SolvedPFact(
        pfact=PFact(fact=fact, prob=prob),
        truth_value=truth_value,
        posterior_prob=posterior,
    )


def _minimal_solution(spfacts):
    """Build a minimal Solution wrapping a list of SolvedPFacts."""
    return Solution(
        number_of_combinations=1,
        number_of_satisfiable_combinations=1,
        number_of_combinations_explored_including_implicit=1,
        confidence=0.99,
        prior_prob=0.5,
        posterior_prob=0.99,
        proportion_of_combinations_explored=1.0,
        ground_pfacts=[(spf.pfact, spf.truth_value) for spf in spfacts],
        solved_pfacts=spfacts,
    )


# ---------------------------------------------------------------------------
# fact_to_sssom_row
# ---------------------------------------------------------------------------

class TestFactToSsomRow:
    def test_equivalent_to_row(self):
        sp = _make_spfact(EquivalentTo(sub="A:1", equivalent="B:2"), posterior=0.95)
        row = fact_to_sssom_row(sp)
        assert row is not None
        assert row["predicate_id"] == "skos:exactMatch"
        assert row["subject_id"] == "A:1"
        assert row["object_id"] == "B:2"
        assert row["confidence"] == "0.95"

    def test_proper_subclass_row(self):
        sp = _make_spfact(ProperSubClassOf(sub="X:1", sup="Y:2"), posterior=0.8)
        row = fact_to_sssom_row(sp)
        assert row is not None
        assert row["predicate_id"] == "skos:narrowMatch"
        assert row["subject_id"] == "X:1"
        assert row["object_id"] == "Y:2"
        assert row["confidence"] == "0.8"

    def test_disjoint_returns_none(self):
        sp = _make_spfact(DisjointWith(sub="A:1", sibling="B:2"))
        assert fact_to_sssom_row(sp) is None

    def test_labels_included(self):
        sp = _make_spfact(EquivalentTo(sub="A:1", equivalent="B:2"))
        labels = {"A:1": "Alpha", "B:2": "Beta"}
        row = fact_to_sssom_row(sp, labels=labels)
        assert row["subject_label"] == "Alpha"
        assert row["object_label"] == "Beta"

    def test_missing_labels(self):
        sp = _make_spfact(EquivalentTo(sub="A:1", equivalent="B:2"))
        row = fact_to_sssom_row(sp, labels={})
        assert row["subject_label"] == ""
        assert row["object_label"] == ""


# ---------------------------------------------------------------------------
# SSSOMRenderer
# ---------------------------------------------------------------------------

class TestSSSOMRenderer:
    def test_render_metadata_header(self):
        spfacts = [_make_spfact(EquivalentTo(sub="HP:1", equivalent="MP:2"))]
        sol = _minimal_solution(spfacts)
        renderer = SSSOMRenderer()
        output = renderer.render(sol)
        assert output.startswith("#")
        assert "mapping_set_id" in output
        assert "mapping_tool: BOOMER" in output

    def test_render_columns(self):
        spfacts = [_make_spfact(EquivalentTo(sub="A:1", equivalent="B:2"))]
        sol = _minimal_solution(spfacts)
        renderer = SSSOMRenderer()
        output = renderer.render(sol)
        # Find the header line (first non-comment line)
        for line in output.splitlines():
            if not line.startswith("#"):
                cols = line.split("\t")
                assert cols == SSSOM_COLUMNS
                break

    def test_filter_accepted_only(self):
        accepted = _make_spfact(
            EquivalentTo(sub="A:1", equivalent="B:2"), truth_value=True,
        )
        rejected = _make_spfact(
            EquivalentTo(sub="C:3", equivalent="D:4"), truth_value=False,
        )
        sol = _minimal_solution([accepted, rejected])
        renderer = SSSOMRenderer()  # default filter_mode="accepted"
        output = renderer.render(sol)
        assert "A:1" in output
        assert "C:3" not in output

    def test_filter_all(self):
        accepted = _make_spfact(
            EquivalentTo(sub="A:1", equivalent="B:2"), truth_value=True,
        )
        rejected = _make_spfact(
            EquivalentTo(sub="C:3", equivalent="D:4"), truth_value=False,
        )
        sol = _minimal_solution([accepted, rejected])
        renderer = SSSOMRenderer(filter_mode="all")
        output = renderer.render(sol)
        assert "A:1" in output
        assert "C:3" in output

    def test_curie_map_includes_entity_prefixes(self):
        spfacts = [_make_spfact(EquivalentTo(sub="HP:1", equivalent="MP:2"))]
        sol = _minimal_solution(spfacts)
        renderer = SSSOMRenderer()
        output = renderer.render(sol)
        assert "HP:" in output
        assert "MP:" in output
        assert "http://purl.obolibrary.org/obo/HP_" in output

    def test_roundtrip(self, tmp_path):
        """Render as SSSOM → parse with parse_sssom_tsv → compare entities."""
        from boomer.sssom_converter import parse_sssom_tsv

        spfacts = [
            _make_spfact(EquivalentTo(sub="HP:001", equivalent="MP:002"), posterior=0.95),
            _make_spfact(ProperSubClassOf(sub="HP:003", sup="MP:004"), posterior=0.80),
        ]
        sol = _minimal_solution(spfacts)
        renderer = SSSOMRenderer()
        output = renderer.render(sol)

        # Write to temp file and parse back
        sssom_path = tmp_path / "test.sssom.tsv"
        sssom_path.write_text(output)
        metadata, rows = parse_sssom_tsv(sssom_path)

        assert metadata["mapping_set_id"] == "boomer:solution"
        assert len(rows) == 2
        assert rows[0]["subject_id"] == "HP:001"
        assert rows[0]["object_id"] == "MP:002"
        assert rows[0]["predicate_id"] == "skos:exactMatch"
        assert rows[1]["predicate_id"] == "skos:narrowMatch"


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

def test_cli_solve_sssom(tmp_path):
    """Solve animals dataset with -O sssom and check output has SSSOM columns."""
    from boomer.cli import cli

    out_file = str(tmp_path / "animals.sssom.tsv")
    runner = CliRunner()
    result = runner.invoke(cli, [
        "solve", "boomer.datasets.animals",
        "-O", "sssom", "-t", "10", "-q", "-o", out_file,
    ])
    assert result.exit_code == 0, result.output
    content = (tmp_path / "animals.sssom.tsv").read_text()
    lines = [l for l in content.splitlines() if not l.startswith("#")]
    assert len(lines) >= 1
    header = lines[0].split("\t")
    assert "subject_id" in header
    assert "predicate_id" in header
    assert "confidence" in header
