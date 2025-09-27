# BOOMER

**BOOMER** (Bayesian OWL Ontology MErgER) is a probabilistic reasoning system for knowledge representation and ontological reasoning with uncertainty.

## Overview

BOOMER enables reasoning over probabilistic facts and taxonomic relationships, finding the most likely consistent interpretation of potentially conflicting assertions. It uses a combination of graph-based reasoning and Bayesian probabilistic inference.

![BOOMER Logo](assets/images/boomer-logo.svg)

## Key Features

- **Probabilistic Knowledge Representation**: Express uncertainty in your knowledge base with probabilities
- **Logical Consistency**: Find the most probable consistent interpretation of competing assertions
- **Ontology Alignment**: Map terms across different ontologies or taxonomies with confidence scores
- **Graph-based Reasoning**: Efficient reasoning over hierarchical structures
- **Command-line Interface**: Easy to use CLI for processing input files
- **Python API**: Programmatic access for integration into your workflows

## Use Cases

BOOMER is designed for:

- **Ontology Alignment**: Mapping terms between different ontologies (e.g., MONDO to ICD10)
- **Disease Classification**: Relating disease terms across different medical coding systems
- **Entity Resolution**: Determining when entities from different sources refer to the same concept
- **Scientific Knowledge Integration**: Combining knowledge from multiple sources with different confidences

## Quick Example

```python
from boomer.io import ptable_to_kb
from boomer.search import solve

# Create a KB from a probability table
with open("path/to/mapping.ptable.tsv") as f:
    kb = ptable_to_kb(f)

# Solve to find most probable consistent solution
solution = solve(kb)

# Analyze high-confidence results
for spf in solution.solved_pfacts:
    if spf.truth_value and spf.posterior_prob > 0.8:
        print(f"High confidence: {spf.pfact.fact} (posterior: {spf.posterior_prob})")
```

### Command Line Usage

```bash
# Process a mapping file
boomer-cli solve mapping.ptable.tsv

# Save results in different formats
boomer-cli solve mapping.ptable.tsv -O json -o solution.json
boomer-cli solve mapping.ptable.tsv -O tsv -o solution.tsv

# Use built-in datasets
boomer-cli solve boomer.datasets.animals
```

## Installation

### For Users

Once BOOMER is published to PyPI:

```bash
# Install with pip
pip install boomer

# Or use uvx for isolated execution
uvx boomer-cli solve input.ptable.tsv
```

### For Developers

Developers should use the modern `uv` workflow:

```bash
# Clone the repository
git clone https://github.com/cmungall/boomer-py.git
cd boomer-py

# Set up development environment
uv sync

# Run during development
uv run boomer-cli --help
uv run pytest  # Run tests
```

## Documentation

### Getting Started
- [Getting Started](getting-started.md) - Quick start guide for using BOOMER
- [Examples](examples.md) - Practical examples and use cases
- [Data Formats](formats.md) - Supported input and output formats (PTable, JSON, YAML)

### Core Concepts
- [Data Model](datamodel.md) - Understanding BOOMER's knowledge representation
- [Reasoning](reasoning.md) - How BOOMER performs probabilistic reasoning
- [Search](search.md) - The search algorithm for finding optimal solutions
- [Partitioning](partitioning.md) - How BOOMER partitions KBs into cliques for efficiency

### Advanced Topics
- [Grid Search](grid-search.md) - Finding optimal hyperparameters
- [Command Line Interface](cli.md) - Complete CLI reference
- [API Reference](api/model.md) - Python API documentation

## License

[Add license information here]