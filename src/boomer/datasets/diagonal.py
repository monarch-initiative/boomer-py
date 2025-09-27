from boomer.model import KB, PFact, EquivalentTo, SearchConfig, SubClassOf, MemberOfDisjointGroup

def create_kb(num_nodes=30, window_size=4) -> KB:
    nodes1 = [f"A{i}" for i in range(num_nodes)]
    nodes2 = [f"B{i}" for i in range(num_nodes)]
    facts = []
    pfacts = []
    labels = {}
    for i in range(num_nodes):
        facts.append(MemberOfDisjointGroup(sub=nodes1[i], group="A"))
        facts.append(MemberOfDisjointGroup(sub=nodes2[i], group="B"))
        labels[nodes1[i]] = f"A {i}"
        labels[nodes2[i]] = f"B {i}"

    for i in range(num_nodes):
        for j in range(i-window_size, i+window_size+1):
            if j >= 0 and j < num_nodes:
                dist = abs(i-j)
                pr = 0.9 ** (dist + 1)
                pfacts.append(PFact(fact=EquivalentTo(sub=nodes1[i], equivalent=nodes2[j]), prob=pr))
    return KB(
        name=f"Diag{num_nodes}x{num_nodes}",
        description=f"A grid-like pattern of equivalence relationships between parallel hierarchies with {num_nodes} nodes, window_size={window_size}",
        comments=f"Tests competing equivalence patterns with 'diagonal' (A1→B1, A2→B2) and 'cross' (A1→B2, A2→B1) mappings",
        facts=facts, 
        pfacts=pfacts,
        labels=labels,
        default_configurations={
            "default": SearchConfig(
                max_candidate_solutions=100,
                max_pfacts_per_clique=20,
            )
        }
        )

kb = create_kb()