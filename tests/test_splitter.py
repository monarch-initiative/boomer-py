import pytest
import boomer.datasets.diagonal as diagonal
from boomer.splitter import split_connected_components


@pytest.mark.parametrize("max_pfacts_per_clique,min_pfacts_per_clique", [(10, 5), (20, 10), (30, 15)])
def test_split_connected_components(max_pfacts_per_clique, min_pfacts_per_clique):
    kb = diagonal.create_kb()
    num_pfacts = len(kb.pfacts)
    pfacts = kb.pfacts
    kbs = list(split_connected_components(kb, max_pfacts_per_clique=max_pfacts_per_clique, min_pfacts_per_clique=min_pfacts_per_clique))
    print(len(kbs))
    total_pfacts = 0
    all_pfacts = []
    for sub_kb in kbs:
        print(f"sub-kb: {len(sub_kb.pfacts)}")
        total_pfacts += len(sub_kb.pfacts)
        for pfact in sub_kb.pfacts:
            if pfact not in all_pfacts:
                all_pfacts.append(pfact)
    for pfact in all_pfacts:
        if pfact not in pfacts:
            print(f"pfact {pfact} in combined sub-kbs but not in pfacts")
    for pfact in pfacts:
        if pfact not in all_pfacts:
            print(f"pfact {pfact} in pfacts but not in combined sub-kbs")
    #assert all_pfacts == pfacts
    assert total_pfacts == num_pfacts
