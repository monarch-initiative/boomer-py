"""
False Bridge Dataset

This dataset demonstrates a scenario where greedy/heuristic search gets trapped by a
high-probability "bridge" fact that creates an unsatisfiable contradiction, while the
correct solution requires rejecting this high-probability fact.

Structure:
- Two islands of internally consistent equivalences
- A hard disjointness constraint between the islands
- A deceptive high-probability bridge that would connect them (causing contradiction)

The correct solution rejects the bridge and keeps islands separate.
"""

from boomer.model import KB, PFact, EquivalentTo, DisjointWith, SubClassOf

# Create the knowledge base
kb = KB(
    name="false_bridge",
    facts=[
        # Add subclass relationships to ensure all entities are in the graph
        SubClassOf(sub="A", sup="Thing"),
        SubClassOf(sub="B", sup="Thing"),
        SubClassOf(sub="C", sup="Thing"),
        SubClassOf(sub="D", sup="Thing"),
        SubClassOf(sub="E", sup="Thing"),
        SubClassOf(sub="F", sup="Thing"),
        SubClassOf(sub="G", sup="Thing"),
        SubClassOf(sub="H", sup="Thing"),
        SubClassOf(sub="X1", sup="Thing"),
        SubClassOf(sub="X2", sup="Thing"),
        SubClassOf(sub="X3", sup="Thing"),
        SubClassOf(sub="X4", sup="Thing"),
        SubClassOf(sub="X5", sup="Thing"),
        SubClassOf(sub="X6", sup="Thing"),
        SubClassOf(sub="X7", sup="Thing"),
        SubClassOf(sub="X8", sup="Thing"),

        # Hard constraint: Islands are disjoint
        # This means nothing from Island 1 can be equivalent to anything from Island 2
        DisjointWith(sub="A", sibling="E"),
    ],
    pfacts=[
        # Island 1: A-B-C-D chain of equivalences (all high probability)
        PFact(fact=EquivalentTo(sub="A", equivalent="B"), prob=0.9),
        PFact(fact=EquivalentTo(sub="A", equivalent="C"), prob=0.9),
        PFact(fact=EquivalentTo(sub="A", equivalent="D"), prob=0.9),
        PFact(fact=EquivalentTo(sub="B", equivalent="C"), prob=0.9),
        PFact(fact=EquivalentTo(sub="B", equivalent="D"), prob=0.9),
        PFact(fact=EquivalentTo(sub="C", equivalent="D"), prob=0.9),

        # Island 2: E-F-G-H chain of equivalences (all high probability)
        PFact(fact=EquivalentTo(sub="E", equivalent="F"), prob=0.9),
        PFact(fact=EquivalentTo(sub="E", equivalent="G"), prob=0.9),
        PFact(fact=EquivalentTo(sub="E", equivalent="H"), prob=0.9),
        PFact(fact=EquivalentTo(sub="F", equivalent="G"), prob=0.9),
        PFact(fact=EquivalentTo(sub="F", equivalent="H"), prob=0.9),
        PFact(fact=EquivalentTo(sub="G", equivalent="H"), prob=0.9),

        # Trick irrelevant axioms
        PFact(fact=EquivalentTo(sub="X1", equivalent="X2"), prob=0.91),
        PFact(fact=EquivalentTo(sub="X2", equivalent="X3"), prob=0.91),
        PFact(fact=EquivalentTo(sub="X3", equivalent="X4"), prob=0.91),
        PFact(fact=EquivalentTo(sub="X4", equivalent="X5"), prob=0.91),
        PFact(fact=EquivalentTo(sub="X5", equivalent="X6"), prob=0.91),
        PFact(fact=EquivalentTo(sub="X6", equivalent="X7"), prob=0.91),
        PFact(fact=EquivalentTo(sub="X7", equivalent="X8"), prob=0.91),
        PFact(fact=EquivalentTo(sub="X8", equivalent="X1"), prob=0.91),
        PFact(fact=DisjointWith(sub="X1", sibling="X8"),prob=0.91),

        # The deceptive bridge: Very high probability but creates contradiction
        # If D≡E is accepted, it merges the islands, violating DisjointWith(A, E)
        # PFact(fact=EquivalentTo(sub="D", equivalent="E"), prob=0.99),
        PFact(fact=SubClassOf(sub="D", sup="E"), prob=0.92),
        PFact(fact=SubClassOf(sub="E", sup="D"), prob=0.92),
    ]
)