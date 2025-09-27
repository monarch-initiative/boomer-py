from boomer.model import KB, PFact, EquivalentTo, SubClassOf, MemberOfDisjointGroup

kb = KB(
    facts=[
        SubClassOf(sub="A2", sup="A1"),
        SubClassOf(sub="B2", sup="B1"),
        MemberOfDisjointGroup(sub="A1", group="A"),
        MemberOfDisjointGroup(sub="A2", group="A"),
        MemberOfDisjointGroup(sub="B1", group="B"),
        MemberOfDisjointGroup(sub="B2", group="B"),
    ],
    pfacts=[
        PFact(fact=EquivalentTo(sub="A1", equivalent="B1"), prob=0.9),
        PFact(fact=EquivalentTo(sub="A2", equivalent="B2"), prob=0.9),
        PFact(fact=EquivalentTo(sub="A1", equivalent="B2"), prob=0.6),
        PFact(fact=EquivalentTo(sub="A2", equivalent="B1"), prob=0.6),
    ],
    name="Quad",
    description="A grid-like pattern of equivalence relationships between parallel hierarchies",
    comments="Tests competing equivalence patterns with 'diagonal' (A1→B1, A2→B2) and 'cross' (A1→B2, A2→B1) mappings",
)
