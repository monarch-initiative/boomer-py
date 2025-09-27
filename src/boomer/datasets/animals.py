from boomer.model import (
    KB,
    PFact,
    EquivalentTo,
    ProperSubClassOf,
    MemberOfDisjointGroup,
)

kb = KB(
    facts=[
        ProperSubClassOf(sub="Felix", sup="Mammalia"),
        ProperSubClassOf(sub="Canus", sup="Mammalia"),
        MemberOfDisjointGroup(sub="cat", group="Common"),
        MemberOfDisjointGroup(sub="dog", group="Common"),
        MemberOfDisjointGroup(sub="furry_animal", group="Common"),
        MemberOfDisjointGroup(sub="Felix", group="Formal"),
        MemberOfDisjointGroup(sub="Canus", group="Formal"),
        MemberOfDisjointGroup(sub="Mammalia", group="Formal"),
    ],
    pfacts=[
        PFact(fact=EquivalentTo(sub="cat", equivalent="Felix"), prob=0.9),
        PFact(fact=EquivalentTo(sub="dog", equivalent="Canus"), prob=0.9),
        PFact(fact=EquivalentTo(sub="furry_animal", equivalent="Mammalia"), prob=0.9),
        PFact(fact=EquivalentTo(sub="cat", equivalent="Canus"), prob=0.1),
        PFact(fact=EquivalentTo(sub="cat", equivalent="Mammalia"), prob=0.1),
        PFact(fact=EquivalentTo(sub="dog", equivalent="Felix"), prob=0.1),
        PFact(fact=EquivalentTo(sub="dog", equivalent="Mammalia"), prob=0.1),
        PFact(fact=EquivalentTo(sub="furry_animal", equivalent="Canus"), prob=0.1),
        PFact(fact=EquivalentTo(sub="furry_animal", equivalent="Felix"), prob=0.1),
    ],
    name="Animals",
    description="An ontology alignment example between common animal names and scientific taxonomy",
    comments="Maps between common terms (cat, dog, furry_animal) and scientific terms (Felix, Canus, Mammalia)",
)
