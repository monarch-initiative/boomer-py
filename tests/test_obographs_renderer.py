"""Tests for the OBOGraphs JSON solution renderer."""

import json

import pytest
from click.testing import CliRunner

from boomer.model import (
    DisjointWith,
    EquivalentTo,
    KB,
    MemberOfDisjointGroup,
    PFact,
    ProperSubClassOf,
    Solution,
    SolvedPFact,
    SubClassOf,
)
from boomer.renderers.obographs_renderer import (
    OBOGraphsRenderer,
    _fact_to_edge,
    _make_node,
    solution_to_obograph,
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
# _make_node
# ---------------------------------------------------------------------------

class TestMakeNode:
    def test_with_label(self):
        node = _make_node("GO:0001234", "some process")
        assert node == {"id": "GO:0001234", "lbl": "some process"}

    def test_without_label(self):
        node = _make_node("CL:0000001")
        assert node == {"id": "CL:0000001"}


# ---------------------------------------------------------------------------
# _fact_to_edge
# ---------------------------------------------------------------------------

class TestFactToEdge:
    def test_equivalent(self):
        edge = _fact_to_edge(EquivalentTo(sub="A:1", equivalent="B:2"))
        assert edge == {"sub": "A:1", "pred": "owl:equivalentClass", "obj": "B:2"}

    def test_subclass(self):
        edge = _fact_to_edge(ProperSubClassOf(sub="X:1", sup="Y:2"))
        assert edge == {"sub": "X:1", "pred": "is_a", "obj": "Y:2"}

    def test_disjoint(self):
        edge = _fact_to_edge(DisjointWith(sub="A:1", sibling="B:2"))
        assert edge == {"sub": "A:1", "pred": "owl:disjointWith", "obj": "B:2"}

    def test_member_group_none(self):
        assert _fact_to_edge(MemberOfDisjointGroup(sub="A:1", group="g")) is None


# ---------------------------------------------------------------------------
# solution_to_obograph
# ---------------------------------------------------------------------------

class TestSolutionToObograph:
    def test_basic_structure(self):
        spfacts = [_make_spfact(EquivalentTo(sub="A:1", equivalent="B:2"))]
        sol = _minimal_solution(spfacts)
        graph = solution_to_obograph(sol)
        assert "graphs" in graph
        g = graph["graphs"][0]
        assert "nodes" in g
        assert "edges" in g
        assert len(g["edges"]) == 1

    def test_only_accepted_edges(self):
        accepted = _make_spfact(EquivalentTo(sub="A:1", equivalent="B:2"), truth_value=True)
        rejected = _make_spfact(EquivalentTo(sub="C:3", equivalent="D:4"), truth_value=False)
        sol = _minimal_solution([accepted, rejected])
        graph = solution_to_obograph(sol)
        edges = graph["graphs"][0]["edges"]
        subs = {e["sub"] for e in edges}
        assert "A:1" in subs
        assert "C:3" not in subs

    def test_include_hard_facts(self):
        spfacts = [_make_spfact(EquivalentTo(sub="A:1", equivalent="B:2"))]
        sol = _minimal_solution(spfacts)
        kb = KB(
            facts=[ProperSubClassOf(sub="B:2", sup="C:3")],
            pfacts=[spfacts[0].pfact],
        )
        graph = solution_to_obograph(sol, kb, include_hard_facts=True)
        edges = graph["graphs"][0]["edges"]
        preds = {(e["sub"], e["pred"]) for e in edges}
        assert ("B:2", "is_a") in preds

    def test_exclude_hard_facts(self):
        spfacts = [_make_spfact(EquivalentTo(sub="A:1", equivalent="B:2"))]
        sol = _minimal_solution(spfacts)
        kb = KB(
            facts=[ProperSubClassOf(sub="B:2", sup="C:3")],
            pfacts=[spfacts[0].pfact],
        )
        graph = solution_to_obograph(sol, kb, include_hard_facts=False)
        edges = graph["graphs"][0]["edges"]
        assert len(edges) == 1  # only the pfact edge

    def test_edge_meta_probabilities(self):
        spfacts = [_make_spfact(EquivalentTo(sub="A:1", equivalent="B:2"), prob=0.9, posterior=0.95)]
        sol = _minimal_solution(spfacts)
        graph = solution_to_obograph(sol)
        edge = graph["graphs"][0]["edges"][0]
        bpvs = edge["meta"]["basicPropertyValues"]
        pred_vals = {bpv["pred"]: bpv["val"] for bpv in bpvs}
        assert pred_vals["boomer:posteriorProbability"] == "0.95"
        assert pred_vals["boomer:priorProbability"] == "0.9"

    def test_node_labels(self):
        spfacts = [_make_spfact(EquivalentTo(sub="A:1", equivalent="B:2"))]
        sol = _minimal_solution(spfacts)
        kb = KB(labels={"A:1": "Alpha", "B:2": "Beta"})
        graph = solution_to_obograph(sol, kb)
        nodes = {n["id"]: n for n in graph["graphs"][0]["nodes"]}
        assert nodes["A:1"]["lbl"] == "Alpha"
        assert nodes["B:2"]["lbl"] == "Beta"


# ---------------------------------------------------------------------------
# OBOGraphsRenderer
# ---------------------------------------------------------------------------

class TestOBOGraphsRenderer:
    def test_valid_json(self):
        spfacts = [_make_spfact(EquivalentTo(sub="A:1", equivalent="B:2"))]
        sol = _minimal_solution(spfacts)
        renderer = OBOGraphsRenderer()
        output = renderer.render(sol)
        parsed = json.loads(output)
        assert "graphs" in parsed

    def test_include_rejected_flag(self):
        accepted = _make_spfact(EquivalentTo(sub="A:1", equivalent="B:2"), truth_value=True)
        rejected = _make_spfact(EquivalentTo(sub="C:3", equivalent="D:4"), truth_value=False)
        sol = _minimal_solution([accepted, rejected])
        renderer = OBOGraphsRenderer(include_rejected=True)
        output = renderer.render(sol)
        parsed = json.loads(output)
        subs = {e["sub"] for e in parsed["graphs"][0]["edges"]}
        assert "C:3" in subs


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

def test_cli_solve_obographs(tmp_path):
    """Solve animals dataset with -O obographs and check output is valid JSON."""
    from boomer.cli import cli

    out_file = str(tmp_path / "animals.obographs.json")
    runner = CliRunner()
    result = runner.invoke(cli, [
        "solve", "boomer.datasets.animals",
        "-O", "obographs", "-t", "10", "-q", "-o", out_file,
    ])
    assert result.exit_code == 0, result.output
    content = (tmp_path / "animals.obographs.json").read_text()
    parsed = json.loads(content)
    assert "graphs" in parsed
    assert len(parsed["graphs"]) >= 1
