"""
CLI tests for the grid_search command.
"""
import json
import yaml

import pytest
from click.testing import CliRunner

from boomer.cli import cli
from boomer.model import SearchConfig, GridSearch, KB, EquivalentTo


def load_sot_equivs(sot_file):
    """Parse curated equivalence pairs from a TSV file into EquivalentTo facts."""
    facts = []
    with open(sot_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            a, b = line.split("\t")
            facts.append(EquivalentTo(sub=a, equivalent=b))
    return facts


@pytest.mark.parametrize("fmt", ["json"])
def test_grid_search_cli(tmp_path, fmt):
    runner = CliRunner()

    # build a simple grid spec: baseline + two hyperparams
    base = SearchConfig()
    grid = GridSearch(
        configurations=[base],
        configuration_matrix={
            "max_pfacts_per_clique": [5, 10],
            "max_candidate_solutions": [10, 15, 20],
        },
    )
    spec_file = tmp_path / f"grid_spec.{fmt}"
    if fmt == "json":
        spec_file.write_text(grid.model_dump_json(indent=2), encoding="utf-8")
    else:
        spec_file.write_text(yaml.dump(grid.model_dump(), sort_keys=False), encoding="utf-8")

    # prepare eval KB from curated eqvs
    sot_facts = load_sot_equivs("tests/input/brain100.solved-equivs.tsv")
    eval_kb = KB(facts=sot_facts)
    eval_file = tmp_path / f"eval_kb.{fmt}"
    if fmt == "json":
        eval_file.write_text(eval_kb.model_dump_json(indent=2), encoding="utf-8")
    else:
        eval_file.write_text(yaml.dump(eval_kb.model_dump(), sort_keys=False), encoding="utf-8")

    out_file = tmp_path / f"results.{fmt}"

    # invoke CLI
    args = [
        "grid-search",
        "tests/input/brain100.ptable.tsv",
        str(spec_file),
        "--eval-kb-file",
        str(eval_file),
        "-d",
        str(tmp_path / "workdir"),
        "-o",
        str(out_file),
    ]
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output

    # load and inspect results
    text = out_file.read_text(encoding="utf-8")
    data = json.loads(text) if fmt == "json" else yaml.safe_load(text)

    # expect 3 * 2 = 6 runs
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) == 6

    # verify first configuration matches first hyperparams
    first_cfg = data["results"][0]["config"]
    assert first_cfg["max_pfacts_per_clique"] == 5
    assert first_cfg["max_candidate_solutions"] == 10

    # check presence of evaluation metrics
    ev = data["results"][0]["evaluation"]
    assert all(k in ev for k in ("tp", "fp", "fn", "precision", "recall", "f1"))
