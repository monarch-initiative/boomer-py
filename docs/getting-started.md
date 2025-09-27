# Getting Started with BOOMER

This guide will help you quickly get up and running with BOOMER, from installation to your first probabilistic reasoning task.

## Installation

### For Users

Once BOOMER is published to PyPI, you can install it using pip:

```bash
pip install boomer
```

Alternatively, you can use uvx for isolated execution without installation:

```bash
# Run BOOMER without installing it globally
uvx boomer-cli solve input.ptable.tsv
```

### For Developers

Developers should use the modern `uv` workflow for development:

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

## Prerequisites

BOOMER requires:

- Python 3.10+
- NetworkX (for graph-based reasoning)
- Pydantic (for data modeling)
- Click (for the command-line interface)

All dependencies are automatically installed when you install BOOMER.

## Basic Concepts

Before diving into code, it's helpful to understand some key concepts:

- **Knowledge Base (KB)**: Collection of facts and probabilistic facts
- **Facts**: Logical assertions like SubClassOf, EquivalentTo, etc.
- **Probabilistic Facts (PFacts)**: Facts with assigned probabilities
- **Solution**: The most probable consistent interpretation of the KB

## Your First BOOMER Project

Let's walk through a simple example of using BOOMER to reason over a small knowledge base.

### 1. Create a Knowledge Base

```python
from boomer.model import KB, PFact, EquivalentTo, ProperSubClassOf

# Create a knowledge base with probabilistic facts
kb = KB(
    name="Animals",
    description="A simple animal taxonomy example",
    pfacts=[
        PFact(fact=EquivalentTo(sub="cat", equivalent="Felix"), prob=0.9),
        PFact(fact=EquivalentTo(sub="dog", equivalent="Canus"), prob=0.9),
        PFact(fact=EquivalentTo(sub="cat", equivalent="Canus"), prob=0.1),
    ]
)
```

### 2. Solve the Knowledge Base

```python
from boomer.search import solve

# Solve the knowledge base
solution = solve(kb)

# Print the solution
print(f"Confidence: {solution.confidence}")
print(f"Posterior probability: {solution.posterior_prob}")
```

### 3. Analyze the Results

```python
# Print the results
for spf in solution.solved_pfacts:
    if spf.truth_value:
        print(f"Accepted: {spf.pfact.fact} (posterior: {spf.posterior_prob})")
    else:
        print(f"Rejected: {spf.pfact.fact} (posterior: {spf.posterior_prob})")
```

## Using Probability Tables

BOOMER supports loading knowledge bases from Probability Table (PTable) files, which provide a compact way to specify probabilistic relationships:

```python
from boomer.io import ptable_to_kb
from boomer.search import solve

# Load a knowledge base from a PTable file
with open("path/to/mapping.ptable.tsv") as f:
    kb = ptable_to_kb(f)

# Solve and analyze
solution = solve(kb)

# Print high-confidence results
for spf in solution.solved_pfacts:
    if spf.posterior_prob > 0.8:
        print(f"{spf.pfact.fact}: {spf.posterior_prob:.3f}")
```

## Command Line Interface

BOOMER provides a command-line interface (`boomer-cli`) with multiple commands:

### Basic CLI Usage

```bash
# Process a PTable file (solve is the default command)
boomer-cli path/to/mapping.ptable.tsv

# Explicitly use the solve command
boomer-cli solve path/to/mapping.ptable.tsv

# Save output to a file
boomer-cli solve path/to/mapping.ptable.tsv --output results.md

# Output in different formats
boomer-cli solve mapping.ptable.tsv -O tsv -o results.tsv
boomer-cli solve mapping.ptable.tsv -O json -o solution.json

# Set a timeout and threshold
boomer-cli solve mapping.ptable.tsv --timeout 30 --threshold 0.9

# Save intermediate solutions to a directory for debugging
boomer-cli solve mapping.ptable.tsv --output-dir intermediate_solutions/

# Combine output file with intermediate solutions directory
boomer-cli solve mapping.ptable.tsv \
  --output final_solution.md \
  --output-dir intermediate_solutions/ \
  --max-solutions 50
```

### Convert Between Formats

```bash
# Convert PTable to JSON
boomer-cli convert input.ptable.tsv -o output.json

# Convert JSON to YAML
boomer-cli convert kb.json -o kb.yaml
```

### Work with Built-in Datasets

```bash
# Use built-in animal dataset
boomer-cli solve boomer.datasets.animals

# Convert built-in dataset to JSON
boomer-cli convert boomer.datasets.family -o family.json
```

### Python API Equivalent

Every CLI command has a Python API equivalent:

```python
from boomer.io import load_kb, save_kb
from boomer.search import solve
from boomer.renderers import MarkdownRenderer

# Load and solve
kb = load_kb('mapping.ptable.tsv')  # Auto-detects format
solution = solve(kb, timeout=30)

# Render results
renderer = MarkdownRenderer(threshold=0.9)
output = renderer.render(solution, kb)

# Save solution
save_kb(solution, 'solution.json', format='json')
```

## Next Steps

Now that you have the basics, you can:

- Learn about [Data Formats](formats.md) supported by BOOMER
- Learn more about [Probability Tables](ptables.md)
- Explore the [Data Model](datamodel.md)
- Understand [Reasoning](reasoning.md) and [Search](search.md) in BOOMER
- Check out the [API Reference](api/model.md) for more details
- Try the [Examples](examples.md) to see BOOMER in action