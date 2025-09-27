from boomer.model import (
    KB,
    PFact,
    EquivalentTo,
    ProperSubClassOf,
    MemberOfDisjointGroup,
)

kb = KB(
    # Deterministic facts
    facts=[
        # Taxonomic structure for role-based terms
        ProperSubClassOf(sub="Child", sup="Person"),
        ProperSubClassOf(sub="Parent", sup="Person"),
        ProperSubClassOf(sub="Sibling", sup="Person"),
        # Taxonomic structure for kinship-based terms
        ProperSubClassOf(sub="Mother", sup="Parent"),
        ProperSubClassOf(sub="Father", sup="Parent"),
        ProperSubClassOf(sub="Son", sup="Child"),
        ProperSubClassOf(sub="Daughter", sup="Child"),
        ProperSubClassOf(sub="Brother", sup="Sibling"),
        ProperSubClassOf(sub="Sister", sup="Sibling"),
        # Disjoint groups
        MemberOfDisjointGroup(sub="Parent", group="FamilyRoles"),
        MemberOfDisjointGroup(sub="Child", group="FamilyRoles"),
        MemberOfDisjointGroup(sub="Sibling", group="FamilyRoles"),
        MemberOfDisjointGroup(sub="Mother", group="Kinship"),
        MemberOfDisjointGroup(sub="Father", group="Kinship"),
        MemberOfDisjointGroup(sub="Son", group="Kinship"),
        MemberOfDisjointGroup(sub="Daughter", group="Kinship"),
        MemberOfDisjointGroup(sub="Brother", group="Kinship"),
        MemberOfDisjointGroup(sub="Sister", group="Kinship"),
    ],
    # Probabilistic facts
    pfacts=[
        # Correct mappings with high probabilities
        PFact(fact=EquivalentTo(sub="Mother", equivalent="FemaleParent"), prob=0.9),
        PFact(fact=EquivalentTo(sub="Father", equivalent="MaleParent"), prob=0.9),
        PFact(fact=EquivalentTo(sub="Son", equivalent="MaleChild"), prob=0.9),
        PFact(fact=EquivalentTo(sub="Daughter", equivalent="FemaleChild"), prob=0.9),
        PFact(fact=EquivalentTo(sub="Brother", equivalent="MaleSibling"), prob=0.9),
        PFact(fact=EquivalentTo(sub="Sister", equivalent="FemaleSibling"), prob=0.9),
        # Incorrect mappings with lower probabilities
        PFact(fact=EquivalentTo(sub="Mother", equivalent="MaleParent"), prob=0.1),
        PFact(fact=EquivalentTo(sub="Father", equivalent="FemaleParent"), prob=0.1),
        PFact(fact=EquivalentTo(sub="Son", equivalent="FemaleChild"), prob=0.1),
        PFact(fact=EquivalentTo(sub="Daughter", equivalent="MaleChild"), prob=0.1),
        PFact(fact=EquivalentTo(sub="Brother", equivalent="FemaleSibling"), prob=0.1),
        PFact(fact=EquivalentTo(sub="Sister", equivalent="MaleSibling"), prob=0.1),
        # Gender relationships
        PFact(fact=ProperSubClassOf(sub="FemaleParent", sup="Parent"), prob=0.95),
        PFact(fact=ProperSubClassOf(sub="MaleParent", sup="Parent"), prob=0.95),
        PFact(fact=ProperSubClassOf(sub="FemaleChild", sup="Child"), prob=0.95),
        PFact(fact=ProperSubClassOf(sub="MaleChild", sup="Child"), prob=0.95),
        PFact(fact=ProperSubClassOf(sub="FemaleSibling", sup="Sibling"), prob=0.95),
        PFact(fact=ProperSubClassOf(sub="MaleSibling", sup="Sibling"), prob=0.95),
    ],
    name="Family",
    description="Family relationships with role-based and kinship-based annotation systems",
    comments="Demonstrates taxonomic relationships, disjoint groups, and gender-specific mappings",
)
