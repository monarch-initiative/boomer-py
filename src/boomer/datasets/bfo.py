from boomer.model import KB, ProperSubClassOf, DisjointSet

kb = KB(
    facts=[
        # Top-level disjoint classes
        DisjointSet(entities=("Entity", "Nothing")),
        # Entity proper subclasses
        ProperSubClassOf(sub="Continuant", sup="Entity"),
        ProperSubClassOf(sub="Occurrent", sup="Entity"),
        # Continuant and Occurrent are disjoint
        DisjointSet(entities=("Continuant", "Occurrent")),
        # Continuant subclasses
        ProperSubClassOf(sub="SpecificallyDependentContinuant", sup="Continuant"),
        ProperSubClassOf(sub="GenericallyDependentContinuant", sup="Continuant"),
        ProperSubClassOf(sub="IndependentContinuant", sup="Continuant"),
        # Continuant subclasses are pairwise disjoint
        DisjointSet(
            entities=(
                "SpecificallyDependentContinuant",
                "GenericallyDependentContinuant",
                "IndependentContinuant",
            )
        ),
        # SpecificallyDependentContinuant subclasses
        ProperSubClassOf(sub="Quality", sup="SpecificallyDependentContinuant"),
        ProperSubClassOf(sub="RealizableEntity", sup="SpecificallyDependentContinuant"),
        DisjointSet(entities=("Quality", "RealizableEntity")),
        # RealizableEntity subclasses
        ProperSubClassOf(sub="Role", sup="RealizableEntity"),
        ProperSubClassOf(sub="Disposition", sup="RealizableEntity"),
        ProperSubClassOf(sub="Function", sup="RealizableEntity"),
        DisjointSet(entities=("Role", "Disposition", "Function")),
        # IndependentContinuant subclasses
        ProperSubClassOf(sub="MaterialEntity", sup="IndependentContinuant"),
        ProperSubClassOf(sub="ImmaterialEntity", sup="IndependentContinuant"),
        DisjointSet(entities=("MaterialEntity", "ImmaterialEntity")),
        # MaterialEntity subclasses
        ProperSubClassOf(sub="Object", sup="MaterialEntity"),
        ProperSubClassOf(sub="FiatObjectPart", sup="MaterialEntity"),
        ProperSubClassOf(sub="ObjectAggregate", sup="MaterialEntity"),
        DisjointSet(entities=("Object", "FiatObjectPart", "ObjectAggregate")),
        # ImmaterialEntity subclasses
        ProperSubClassOf(sub="Site", sup="ImmaterialEntity"),
        ProperSubClassOf(sub="SpatialRegion", sup="ImmaterialEntity"),
        ProperSubClassOf(sub="ContinuantFiatBoundary", sup="ImmaterialEntity"),
        DisjointSet(entities=("Site", "SpatialRegion", "ContinuantFiatBoundary")),
        # SpatialRegion subclasses
        ProperSubClassOf(sub="ZeroDimensionalSpatialRegion", sup="SpatialRegion"),
        ProperSubClassOf(sub="OneDimensionalSpatialRegion", sup="SpatialRegion"),
        ProperSubClassOf(sub="TwoDimensionalSpatialRegion", sup="SpatialRegion"),
        ProperSubClassOf(sub="ThreeDimensionalSpatialRegion", sup="SpatialRegion"),
        DisjointSet(
            entities=(
                "ZeroDimensionalSpatialRegion",
                "OneDimensionalSpatialRegion",
                "TwoDimensionalSpatialRegion",
                "ThreeDimensionalSpatialRegion",
            )
        ),
        # Occurrent subclasses
        ProperSubClassOf(sub="Process", sup="Occurrent"),
        ProperSubClassOf(sub="ProcessBoundary", sup="Occurrent"),
        ProperSubClassOf(sub="TemporalRegion", sup="Occurrent"),
        ProperSubClassOf(sub="SpatiotemporalRegion", sup="Occurrent"),
        DisjointSet(
            entities=(
                "Process",
                "ProcessBoundary",
                "TemporalRegion",
                "SpatiotemporalRegion",
            )
        ),
        # TemporalRegion subclasses
        ProperSubClassOf(sub="ZeroDimensionalTemporalRegion", sup="TemporalRegion"),
        ProperSubClassOf(sub="OneDimensionalTemporalRegion", sup="TemporalRegion"),
        DisjointSet(
            entities=("ZeroDimensionalTemporalRegion", "OneDimensionalTemporalRegion")
        ),
    ],
    name="BFO2",
    description="Basic Formal Ontology 2.0 upper ontology with proper subclass hierarchy and disjointness constraints",
    comments="Implements the core BFO2 hierarchy with Entity as root, major divisions into Continuant/Occurrent, and comprehensive disjointness axioms using DisjointSet for efficient encoding",
)
