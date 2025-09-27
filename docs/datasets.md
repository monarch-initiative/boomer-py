# BOOMER Datasets

This document describes the example knowledge bases (KBs) for testing and demonstrating BOOMER's probabilistic reasoning capabilities.

## Overview

Each dataset defines a knowledge base (`kb`) that contains:
- Deterministic facts (certainty of 1.0)
- Probabilistic facts (PFacts) with assigned probabilities
- Metadata (name, description, comments)

These datasets represent different patterns of knowledge representation and reasoning challenges.

## Available Datasets

### Animals Dataset

A classic ontology alignment example between common and scientific taxonomies:

- **Name**: "Animals"
- **Description**: "A classic ontology alignment example between common animal names and scientific taxonomy"
- **Common terms**: "cat", "dog", "furry_animal" 
- **Scientific terms**: "Felix", "Canus", "Mammalia"
- **Structure**: 
  - High probability mappings between correct pairs (0.9)
  - Low probability mappings between incorrect pairs (0.1)
  - Disjoint group membership for common vs. formal terms
  - Taxonomic hierarchy with proper subclass relationships

This dataset demonstrates reasoning about entity equivalence across different taxonomies.

### Quad Dataset

A grid-like pattern of equivalence relationships:

- **Name**: "Quad"
- **Description**: "A grid-like pattern of equivalence relationships between parallel hierarchies"
- **Structure**:
  - Two parallel hierarchies (A1→A2 and B1→B2)
  - Probabilistic equivalence relationships between the hierarchies
  - High probability for "diagonal" mappings (A1-B1, A2-B2)
  - Medium probability for "cross" mappings (A1-B2, A2-B1)

This dataset tests the reasoner's ability to handle competing equivalence relationships.

### Ladder Dataset

A "ladder" pattern with parallel hierarchies and strong equivalence ties:

- **Name**: "Ladder"
- **Description**: "A ladder pattern with parallel hierarchies connected by equivalence relationships"
- **Structure**:
  - Two parallel chains: L0←L1←L2←L3←L4 and R0←R1←R2←R3←R4
  - Deterministic equivalence between corresponding levels (L0=R0, L1=R1, etc.)
  - Low probability facts that potentially create logical inconsistencies

This dataset tests reasoning with longer transitive chains and the interaction between deterministic and probabilistic assertions.

### Family Dataset

A family relationships model with role-based and kinship-based annotation systems:

- **Name**: "Family"
- **Description**: "Family relationships with role-based and kinship-based annotation systems"
- **Structure**:
  - Role-based terms: "Parent", "Child", "Sibling"
  - Kinship terms: "Mother", "Father", "Son", "Daughter", "Brother", "Sister"
  - Gender-specific terms: "FemaleParent", "MaleParent", etc.
  - Taxonomic relationships (e.g., Mother is a Parent)
  - Disjoint groups (e.g., Parent and Child are disjoint)
  - High probability for correct mappings (0.9)
  - Low probability for incorrect mappings (0.1)

This dataset tests reasoning about complex hierarchical relationships with multiple overlapping categories.

### Multilingual Dataset

A cross-language terminology mapping with semantic nuances:

- **Name**: "Multilingual"
- **Description**: "Cross-language terminology mapping with semantic nuances in English, Spanish, and German"
- **Structure**:
  - Three language groups: English, Spanish, German
  - Concepts with nuanced meanings across languages:
    - "privacy" (EN) vs "privacidad" (ES) vs "Datenschutz"/"Privatsphäre" (DE)
    - "home" (EN) vs "casa"/"hogar" (ES) vs "Zuhause"/"Heim" (DE)
    - "mind" (EN) vs "mente" (ES) vs "Geist"/"Verstand" (DE)
  - Varying probabilities based on semantic alignment quality
  - Some concepts with multiple possible translations of different strengths

This dataset tests BOOMER's ability to handle subtle semantic differences between languages and choose optimal mappings among competing translations with varying degrees of semantic overlap.

## Using the Datasets

```python
import boomer.datasets.animals as animals
from boomer.search import solve

# Access the knowledge base
kb = animals.kb

# Solve it to find the most consistent interpretation
solution = solve(kb)
```

## Creating New Datasets

To create a new dataset, define a knowledge base with the appropriate facts and probabilistic facts:

```python
from boomer.model import KB, PFact, EquivalentTo, ProperSubClassOf

kb = KB(
    # List of deterministic facts
    [
        ProperSubClassOf("A", "B"),
        ProperSubClassOf("B", "C"),
    ],
    # List of probabilistic facts
    [
        PFact(EquivalentTo("X", "A"), 0.8),
        PFact(EquivalentTo("Y", "B"), 0.7),
        PFact(EquivalentTo("Y", "A"), 0.1),
    ]
)
```