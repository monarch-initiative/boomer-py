"""Example using Cornelia de Lange Syndrome to demonstrate probabilistic disease phenotypes."""

from boomer.model import KB, PFact, SubClassOf, DisjointWith

cdls = KB(
    name="Disease",
    description="Example using Cornelia de Lange Syndrome",
    facts=[
        # DisjointWith("CdLS", "No CdLS"),
        # SubClassOf("No CdLS", "disease absent"),
        # SubClassOf("CdLS", "disease present"),
        # SubClassOf("synophrys", "facial features"),
        # SubClassOf("long eyelashes", "facial features"),
        # SubClassOf("susceptibility to infection", "immune system dysfunction"),
        # SubClassOf("patient", "disease present"),
        DisjointWith(sub="CdLS", sibling="!CdLS"),
        SubClassOf(sub="!CdLS", sup="root"),
        SubClassOf(sub="CdLS", sup="root"),
        # OneOf("CdLS", "!CdLS"),
        # DisjointWith("synophrys", "no synophrys"),
        # DisjointWith("long eyelashes", "no long eyelashes"),
        # DisjointWith("susceptibility to infection", "no susceptibility to infection"),
        # SubClassOf("no facial features", "no synophrys"),
        # SubClassOf("no facial features", "no long eyelashes"),
        # SubClassOf("no immune system dysfunction", "no susceptibility to infection"),
    ],
    pfacts=[
        PFact(fact=SubClassOf(sub="CdLS", sup="synophrys"), prob=1.0),
        PFact(fact=SubClassOf(sub="CdLS", sup="long eyelashes"), prob=0.90),
        PFact(
            fact=SubClassOf(sub="CdLS", sup="susceptibility to infection"), prob=0.05
        ),
        PFact(fact=SubClassOf(sub="synophrys", sup="!CdLS"), prob=0.01),
        PFact(fact=SubClassOf(sub="long eyelashes", sup="!CdLS"), prob=0.01),
        PFact(
            fact=SubClassOf(sub="susceptibility to infection", sup="!CdLS"), prob=0.01
        ),
        # PFact(SubClassOf("!CdLS", "synophrys"), 0.01),
        # PFact(SubClassOf("!CdLS", "long eyelashes"), 0.01),
        # PFact(SubClassOf("!CdLS", "susceptibility to infection"), 0.10),
        # PFact(NegatedFact(SubClassOf("No CdLS", "synophrys")), 0.95),
        # PFact(NegatedFact(SubClassOf("No CdLS", "long eyelashes")), 0.9),
        # PFact(NegatedFact(SubClassOf("No CdLS", "susceptibility to infection")), 0.9),
    ],
)
patient1 = cdls.extend(
    name="Patient 1",
    description="Patient with phenotypes clearly consistent with Cornelia de Lange Syndrome",
    facts=[
        # SubClassOf("Patient 1", "patient"),
    ],
    hypotheses=[
        SubClassOf(sub="Patient 1", sup="CdLS"),
        SubClassOf(sub="Patient 1", sup="!CdLS"),
    ],
    pfacts=[
        PFact(fact=SubClassOf(sub="Patient 1", sup="synophrys"), prob=0.95),
        PFact(fact=SubClassOf(sub="Patient 1", sup="long eyelashes"), prob=0.90),
        # PFact(SubClassOf("Patient 1", "no susceptibility to infection"), 0.95),
    ],
)
patient2 = cdls.extend(
    name="Patient 2",
    description="Patient with phenotypes clearly INconsistent with Cornelia de Lange Syndrome",
    hypotheses=[
        SubClassOf(sub="Patient 2", sup="CdLS"),
    ],
    pfacts=[
        PFact(fact=SubClassOf(sub="Patient 2", sup="synophrys"), prob=0.01),
        PFact(fact=SubClassOf(sub="Patient 2", sup="long eyelashes"), prob=0.01),
    ],
)
