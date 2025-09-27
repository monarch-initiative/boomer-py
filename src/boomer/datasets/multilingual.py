from boomer.model import (
    KB,
    PFact,
    EquivalentTo,
    ProperSubClassOf,
    MemberOfDisjointGroup,
)

"""
Multilingual Dataset

This dataset models terms across three languages (English, Spanish, German) with subtle 
semantic differences. Some concepts don't perfectly align across languages, requiring 
probabilistic mappings to capture nuanced semantic slippage.

Examples:
- "privacy" (EN) vs "privacidad" (ES) vs "Datenschutz"/"Privatsphäre" (DE)
- "home" (EN) vs "casa"/"hogar" (ES) vs "Zuhause"/"Heim" (DE)
- "mind" (EN) vs "mente" (ES) vs "Geist"/"Verstand" (DE)
"""

kb = KB(
    # Deterministic facts
    facts=[
        # English terms hierarchy
        ProperSubClassOf(sub="privacy", sup="concept"),
        ProperSubClassOf(sub="home", sup="concept"),
        ProperSubClassOf(sub="mind", sup="concept"),
        # Spanish terms hierarchy
        ProperSubClassOf(sub="privacidad", sup="concepto"),
        ProperSubClassOf(sub="casa", sup="concepto"),
        ProperSubClassOf(sub="hogar", sup="concepto"),
        ProperSubClassOf(sub="mente", sup="concepto"),
        # German terms hierarchy
        ProperSubClassOf(sub="Datenschutz", sup="Begriff"),
        ProperSubClassOf(sub="Privatsphäre", sup="Begriff"),
        ProperSubClassOf(sub="Zuhause", sup="Begriff"),
        ProperSubClassOf(sub="Heim", sup="Begriff"),
        ProperSubClassOf(sub="Geist", sup="Begriff"),
        ProperSubClassOf(sub="Verstand", sup="Begriff"),
        # Language group membership
        MemberOfDisjointGroup(sub="privacy", group="English"),
        MemberOfDisjointGroup(sub="home", group="English"),
        MemberOfDisjointGroup(sub="mind", group="English"),
        MemberOfDisjointGroup(sub="concept", group="English"),
        MemberOfDisjointGroup(sub="privacidad", group="Spanish"),
        MemberOfDisjointGroup(sub="casa", group="Spanish"),
        MemberOfDisjointGroup(sub="hogar", group="Spanish"),
        MemberOfDisjointGroup(sub="mente", group="Spanish"),
        MemberOfDisjointGroup(sub="concepto", group="Spanish"),
        MemberOfDisjointGroup(sub="Datenschutz", group="German"),
        MemberOfDisjointGroup(sub="Privatsphäre", group="German"),
        MemberOfDisjointGroup(sub="Zuhause", group="German"),
        MemberOfDisjointGroup(sub="Heim", group="German"),
        MemberOfDisjointGroup(sub="Geist", group="German"),
        MemberOfDisjointGroup(sub="Verstand", group="German"),
        MemberOfDisjointGroup(sub="Begriff", group="German"),
    ],
    # Probabilistic facts - cross-language mappings with semantic nuances
    pfacts=[
        # Privacy concept mappings
        PFact(
            fact=EquivalentTo(sub="privacy", equivalent="privacidad"), prob=0.9
        ),  # Good match
        PFact(
            fact=EquivalentTo(sub="privacy", equivalent="Privatsphäre"), prob=0.7
        ),  # Partial match (personal privacy)
        PFact(
            fact=EquivalentTo(sub="privacy", equivalent="Datenschutz"), prob=0.6
        ),  # Partial match (data privacy)
        # Home concept mappings
        PFact(
            fact=EquivalentTo(sub="home", equivalent="casa"), prob=0.8
        ),  # Good match but casa is more about the physical building
        PFact(
            fact=EquivalentTo(sub="home", equivalent="hogar"), prob=0.9
        ),  # Better match for the emotional concept of home
        PFact(
            fact=EquivalentTo(sub="home", equivalent="Zuhause"), prob=0.9
        ),  # Good match
        PFact(
            fact=EquivalentTo(sub="home", equivalent="Heim"), prob=0.7
        ),  # Partial match (more formal or institutional)
        # Mind concept mappings
        PFact(
            fact=EquivalentTo(sub="mind", equivalent="mente"), prob=0.8
        ),  # Good match
        PFact(
            fact=EquivalentTo(sub="mind", equivalent="Geist"), prob=0.6
        ),  # Partial match (more spiritual/consciousness aspect)
        PFact(
            fact=EquivalentTo(sub="mind", equivalent="Verstand"), prob=0.7
        ),  # Partial match (more reasoning/intellect aspect)
        # Cross-language incorrect mappings
        PFact(fact=EquivalentTo(sub="privacy", equivalent="casa"), prob=0.1),
        PFact(fact=EquivalentTo(sub="privacy", equivalent="mente"), prob=0.1),
        PFact(fact=EquivalentTo(sub="privacy", equivalent="Zuhause"), prob=0.1),
        PFact(fact=EquivalentTo(sub="home", equivalent="privacidad"), prob=0.1),
        PFact(fact=EquivalentTo(sub="home", equivalent="mente"), prob=0.1),
        PFact(fact=EquivalentTo(sub="home", equivalent="Datenschutz"), prob=0.1),
        PFact(fact=EquivalentTo(sub="mind", equivalent="privacidad"), prob=0.1),
        PFact(fact=EquivalentTo(sub="mind", equivalent="hogar"), prob=0.1),
        PFact(fact=EquivalentTo(sub="mind", equivalent="Privatsphäre"), prob=0.1),
        # German specific nuanced relationships
        PFact(
            fact=EquivalentTo(sub="Datenschutz", equivalent="Privatsphäre"), prob=0.4
        ),  # Related but distinct concepts
        PFact(
            fact=EquivalentTo(sub="Zuhause", equivalent="Heim"), prob=0.5
        ),  # Related but nuanced difference
        PFact(
            fact=EquivalentTo(sub="Geist", equivalent="Verstand"), prob=0.5
        ),  # Related but nuanced difference
        # Spanish specific nuanced relationships
        PFact(
            fact=EquivalentTo(sub="casa", equivalent="hogar"), prob=0.6
        ),  # Related but nuanced difference
    ],
    name="Multilingual",
    description="Cross-language terminology mapping with semantic nuances in English, Spanish, and German",
    comments="Demonstrates how BOOMER can handle subtle semantic differences between languages and choose optimal mappings",
)
