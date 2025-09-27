# Examples

This page contains practical examples of using BOOMER for various knowledge representation and reasoning tasks.

## Example 1: Basic Animal Taxonomy

This example demonstrates a simple taxonomy with probabilistic relationships between common and scientific names.

```python
from boomer.model import KB, PFact, EquivalentTo, ProperSubClassOf
from boomer.search import solve
from boomer.renderers.markdown_renderer import MarkdownRenderer

# Create a knowledge base with facts about animals
kb = KB(
    name="Animal Taxonomy",
    description="Mapping common animal names to scientific names",
    # Deterministic facts
    facts=[
        ProperSubClassOf("Felix", "Mammalia"),
        ProperSubClassOf("Canus", "Mammalia"),
    ],
    # Probabilistic facts
    pfacts=[
        PFact(fact=EquivalentTo(sub="cat", equivalent="Felix"), prob=0.9),
        PFact(fact=EquivalentTo(sub="dog", equivalent="Canus"), prob=0.9),
        PFact(fact=EquivalentTo(sub="cat", equivalent="Canus"), prob=0.1),
        PFact(fact=EquivalentTo(sub="dog", equivalent="Felix"), prob=0.1),
    ]
)

# Solve the knowledge base
solution = solve(kb)

# Print the solution in Markdown format
renderer = MarkdownRenderer()
print(renderer.render(solution, kb))

# Print high confidence results
print("\nHigh confidence mappings:")
for spf in solution.solved_pfacts:
    if spf.truth_value and spf.posterior_prob > 0.8:
        print(f"{spf.pfact.fact} (posterior: {spf.posterior_prob:.4f})")
```

## Example 2: Disease Classification

This example shows how to use BOOMER to align disease classifications from different sources.

```python
from boomer.model import KB, PFact, EquivalentTo, MemberOfDisjointGroup
from boomer.search import solve

# Create a knowledge base for disease classification
kb = KB(
    name="Disease Mapping",
    description="Mapping between MONDO and ICD10 disease codes",
    facts=[
        # Declare disjoint groups for different classification systems
        MemberOfDisjointGroup(sub="MONDO:0000001", group="MONDO"),
        MemberOfDisjointGroup(sub="MONDO:0000023", group="MONDO"),
        MemberOfDisjointGroup(sub="ICD10:K72.0", group="ICD10"),
        MemberOfDisjointGroup(sub="ICD10:K72.1", group="ICD10"),
    ],
    pfacts=[
        # Probabilistic mappings between systems
        PFact(fact=EquivalentTo(sub="MONDO:0000023", equivalent="ICD10:K72.0"), prob=0.8),
        PFact(fact=EquivalentTo(sub="MONDO:0000001", equivalent="ICD10:K72.1"), prob=0.7),
        PFact(fact=EquivalentTo(sub="MONDO:0000023", equivalent="ICD10:K72.1"), prob=0.3),
    ]
)

# Solve with timeout
from boomer.model import SearchConfig
config = SearchConfig(timeout_seconds=10)
solution = solve(kb, config)

# Print results
print(f"Solution confidence: {solution.confidence:.4f}")
for spf in solution.solved_pfacts:
    if spf.truth_value:
        print(f"Accepted: {spf.pfact.fact} ({spf.posterior_prob:.4f})")
    else:
        print(f"Rejected: {spf.pfact.fact} ({spf.posterior_prob:.4f})")
```

## Example 3: Using Probability Tables

This example demonstrates loading a knowledge base from a probability table file.

```python
from boomer.io import ptable_to_kb
from boomer.search import solve
from boomer.model import SearchConfig

# Load knowledge base from a PTable file
with open("tests/input/MONDO_0000023.ptable.tsv") as f:
    kb = ptable_to_kb(
        f,
        name="Acute Liver Failure Mapping",
        description="Mapping MONDO terms to ORDO and ICD10"
    )

# Configure the search
config = SearchConfig(
    max_iterations=100000,
    max_candidate_solutions=1000,
    timeout_seconds=30
)

# Solve the knowledge base
solution = solve(kb, config)

# Print the number of combinations explored
print(f"Explored {solution.number_of_combinations} combinations")
print(f"Found {solution.number_of_satisfiable_combinations} satisfiable combinations")

# Print the most confident mappings
for spf in solution.solved_pfacts:
    if spf.truth_value and spf.posterior_prob > 0.9:
        print(f"High confidence: {spf.pfact.fact} ({spf.posterior_prob:.4f})")
```

## Example 4: Command Line Usage

This example shows how to use the BOOMER command-line interface.

### Basic CLI Examples

```bash
# Basic usage (solve is the default command)
boomer-cli tests/input/MONDO_0000023.ptable.tsv

# Explicitly use solve command
boomer-cli solve tests/input/MONDO_0000023.ptable.tsv

# Save output to a file in Markdown format
boomer-cli solve tests/input/MONDO_0000023.ptable.tsv --output results.md

# Output in different formats
boomer-cli solve tests/input/MONDO_0000023.ptable.tsv -O tsv -o results.tsv
boomer-cli solve tests/input/MONDO_0000023.ptable.tsv -O json -o solution.json
boomer-cli solve tests/input/MONDO_0000023.ptable.tsv -O yaml -o solution.yaml

# Customize the search parameters
boomer-cli solve tests/input/MONDO_0000023.ptable.tsv \
  --name "Acute Liver Failure" \
  --max-solutions 100 \
  --timeout 20 \
  --threshold 0.95

# Use built-in datasets
boomer-cli solve boomer.datasets.animals
boomer-cli solve boomer.datasets.family -O json -o family_solution.json

# Convert between formats
boomer-cli convert input.ptable.tsv -o output.json
boomer-cli convert kb.json -o kb.yaml
boomer-cli convert boomer.datasets.animals -o animals.json

# Merge multiple knowledge bases
boomer-cli merge file1.json file2.yaml file3.ptable.tsv -o merged.json

# Extract subset of facts
boomer-cli extract full_kb.json entity_ids.txt -o subset.json

# Evaluate a solution
boomer-cli eval gold_standard.json solution.json -o evaluation.json

# Grid search for optimal parameters
boomer-cli grid-search kb.yaml grid_spec.json -e gold.yaml -o results.json

# Get help
boomer-cli --help
boomer-cli solve --help
boomer-cli convert --help
```

### Python API Equivalents

```python
# Equivalent to: boomer-cli solve input.ptable.tsv -O json -o solution.json
from boomer.io import load_kb, save_solution
from boomer.search import solve

kb = load_kb('input.ptable.tsv')
solution = solve(kb)
save_solution(solution, 'solution.json', format='json')

# Equivalent to: boomer-cli convert input.ptable.tsv -o output.yaml
from boomer.io import load_kb, save_kb

kb = load_kb('input.ptable.tsv')
save_kb(kb, 'output.yaml', format='yaml')

# Equivalent to: boomer-cli merge file1.json file2.json -o merged.json
from boomer.io import load_kb, save_kb
from boomer.model import merge_kbs

kb1 = load_kb('file1.json')
kb2 = load_kb('file2.json')
merged = merge_kbs([kb1, kb2])
save_kb(merged, 'merged.json', format='json')
```

## Example 5: Custom Renderer

This example shows how to create a custom renderer for the solution.

```python
from boomer.renderers.renderer import Renderer
from boomer.model import Solution
from boomer.io import ptable_to_kb
from boomer.search import solve

# Create a custom renderer for JSON output
class JsonRenderer(Renderer):
    def render(self, solution: Solution, kb: Optional[KB] = None) -> str:
        import json

        # Convert solution to a dictionary
        result = {
            "confidence": solution.confidence,
            "prior_probability": solution.prior_prob,
            "posterior_probability": solution.posterior_prob,
            "combinations_explored": solution.number_of_combinations,
            "satisfiable_combinations": solution.number_of_satisfiable_combinations,
            "time_elapsed": solution.time_elapsed,
            "kb_name": kb.name if kb else None,
            "facts": []
        }

        # Add facts to the result
        for spf in solution.solved_pfacts:
            if spf.truth_value:
                result["facts"].append({
                    "fact": str(spf.pfact.fact),
                    "prior": spf.pfact.prob,
                    "posterior": spf.posterior_prob
                })

        # Return as formatted JSON
        return json.dumps(result, indent=2)

# Use the custom renderer
with open("tests/input/MONDO_0000023.ptable.tsv") as f:
    kb = ptable_to_kb(f)
solution = solve(kb)
renderer = JsonRenderer()
json_output = renderer.render(solution, kb)
print(json_output)
```

These examples demonstrate different ways to use BOOMER for knowledge representation and reasoning tasks. You can adapt them to your specific needs and datasets.