# BOOMER-PY

BOOMER-PY (Bayesian OWL Ontology MErgER in Python) is a probabilistic reasoning system for knowledge representation and ontological reasoning with uncertainty.

## Overview

BOOMER-PY enables reasoning over probabilistic facts and taxonomic relationships, finding the most likely consistent interpretation of potentially conflicting assertions. It uses a combination of graph-based reasoning and Bayesian probabilistic inference.

Key features:
- Represent probabilistic ontological statements
- Reason over class subsumption hierarchies
- Evaluate class equivalence relationships
- Detect and resolve logical inconsistencies
- Calculate posterior probabilities for each assertion

## Core Concepts

- **Knowledge Base (KB)**: Collection of facts and probabilistic facts (PFacts)
- **Facts**: Logical assertions about entity relationships
  - SubClassOf: A is a subclass of B
  - ProperSubClassOf: A is a proper subclass of B (A � B)
  - EquivalentTo: A is equivalent to B
  - NotInSubsumptionWith: A is not in a subsumption relationship with B
  - MemberOfDisjointGroup: A belongs to disjoint group G
- **Probabilistic Facts**: Facts with assigned probabilities
- **Reasoning**: Logical deduction over facts to find satisfiable solutions
- **Search**: Exploration of possible combinations of assertions

## Use Cases

BOOMER-PY is designed for:
- Merging ontologies with uncertain mapping relationships
- Reasoning with probabilistic taxonomies
- Resolving conflicts in knowledge bases
- Scientific knowledge representation with uncertainty

## Example

```python
from boomer.model import KB, PFact, EquivalentTo
from boomer.search import solve
from boomer.renderers.markdown_renderer import MarkdownRenderer

# Create a knowledge base with probabilistic facts
kb = KB(
    pfacts=[
        PFact(EquivalentTo("cat", "Felix"), 0.9),
        PFact(EquivalentTo("dog", "Canus"), 0.9),
        PFact(EquivalentTo("cat", "Canus"), 0.1),
    ]
)

# Solve to find most probable consistent solution
solution = solve(kb)

# Display results
renderer = MarkdownRenderer()
print(renderer.render(solution))
```

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/boomer-py.git
cd boomer-py

# Install dependencies
pip install .
```

## Development

BOOMER-PY uses:
- NetworkX for graph-based reasoning
- Pydantic for data modeling
- Pytest for testing

To run tests:
```bash
make test
```
