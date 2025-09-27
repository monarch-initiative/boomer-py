# Probability Tables

## Overview

Probability Tables (PTables) provide a compact way to specify probabilistic relationships between entities in a Knowledge Base (KB). They are particularly useful for working with ontology alignment problems where multiple sources need to be integrated.

## File Format

A Probability Table is a Tab-Separated Values (TSV) file with 6 columns:

1. **Subject ID**: The identifier for the subject entity
2. **Object ID**: The identifier for the object entity
3. **P(SubClassOf)**: Probability that Subject is a subclass of Object (range: 0.0-1.0)
4. **P(SuperClassOf)**: Probability that Object is a subclass of Subject (range: 0.0-1.0)
5. **P(EquivalentTo)**: Probability that Subject and Object are equivalent (range: 0.0-1.0)
6. **P(DisjointWith)**: Probability that Subject and Object are not in a subsumption relationship (range: 0.0-1.0)

Example row:
```
ORDO:464724	MONDO:0000023	0.033333333333333326	0.033333333333333326	0.9	0.033333333333333326
```

This specifies:
- Subject: ORDO:464724
- Object: MONDO:0000023
- P(ORDO:464724 SubClassOf MONDO:0000023) = 0.033...
- P(MONDO:0000023 SubClassOf ORDO:464724) = 0.033...
- P(ORDO:464724 EquivalentTo MONDO:0000023) = 0.9
- P(ORDO:464724 DisjointWith MONDO:0000023) = 0.033...

## Interpretation

Each row in a PTable generates four probabilistic facts, one for each possible relationship between the subject and object:

1. ProperSubClassOf(Subject, Object)
2. ProperSubClassOf(Object, Subject)
3. EquivalentTo(Subject, Object)
4. NotInSubsumptionWith(Subject, Object)

Additionally, each unique entity ID is assigned to a disjoint group based on its prefix (e.g., "MONDO", "ORDO", "ICD10CM"). This helps model the constraint that terms from different ontologies should not be confused.

## Usage in BOOMER

To use a Probability Table with BOOMER:

```python
from boomer.io import ptable_to_kb
from boomer.search import solve

# Create a KB directly from a PTable file
kb = ptable_to_kb(
    "path/to/file.ptable.tsv",
    name="My KB",  # Optional, defaults to filename
    description="Description of the KB"
)

# Solve the KB
solution = solve(kb)

# Analyze the results
for spf in solution.solved_pfacts:
    if spf.truth_value and spf.posterior_prob > 0.8:
        print(f"High confidence: {spf.pfact.fact} (posterior: {spf.posterior_prob})")
```

## Common Use Cases

PTables are particularly useful for:

1. **Ontology Alignment**: Mapping terms between different ontologies (e.g., MONDO to ICD10)
2. **Disease Classification**: Relating disease terms across different medical coding systems
3. **Entity Resolution**: Determining when entities from different sources refer to the same concept

## Generating PTables

PTables can be created:

1. Manually, for small test cases
2. Using machine learning to generate relationship probabilities
3. From existing ontology mappings with confidence values
4. By converting other probabilistic relationship formats

## Limitations

- Each row only models the direct relationship between two entities
- More complex relationships involving more than two entities require multiple rows
- The sum of probabilities in a row does not need to equal 1.0, as the relationships are not mutually exclusive