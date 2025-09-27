# Data Formats

BOOMER supports multiple data formats for knowledge bases, making it easy to work with different data sources and integrate with various workflows.

## Supported Formats

### Input Formats
- **PTable** (`.ptable.tsv`, `.tsv`) - Tab-separated probability tables
- **JSON** (`.json`) - JSON serialization of Pydantic models
- **YAML** (`.yaml`, `.yml`) - YAML serialization of Pydantic models
- **Python** (`py`) - Python modules with a `kb` attribute

### Output Formats
- **Markdown** - Human-readable reports (default)
- **TSV** - Tab-separated values for downstream processing
- **JSON** - Machine-readable JSON
- **YAML** - Machine-readable YAML

### Future Support
- **OWL** - Web Ontology Language support is planned for future releases

## Format Details

### PTable Format

Probability tables are tab-separated files that compactly represent probabilistic facts:

```tsv
# Example: disease_mappings.ptable.tsv
EquivalentTo	MONDO:0000023	ICD10:K72.0	0.8
EquivalentTo	MONDO:0000023	ICD10:K72.1	0.3
ProperSubClassOf	MONDO:0000023	Disease	1.0
DisjointWith	ICD10:K72.0	ICD10:K72.1	1.0
```

Format specification:
- Column 1: Fact type (EquivalentTo, ProperSubClassOf, DisjointWith, etc.)
- Column 2+: Arguments for the fact
- Last column: Probability (0.0 to 1.0)

### YAML Format

YAML provides a human-readable structured format for knowledge bases:

```yaml
# Example: animals.yaml
name: Animal Taxonomy
description: Mapping common animal names to scientific names

# Deterministic facts (probability = 1.0)
facts:
  - fact_type: ProperSubClassOf
    sub: Felix
    sup: Mammalia
  - fact_type: ProperSubClassOf
    sub: Canus
    sup: Mammalia
  - fact_type: MemberOfDisjointGroup
    sub: cat
    group: Common
  - fact_type: MemberOfDisjointGroup
    sub: dog
    group: Common
  - fact_type: MemberOfDisjointGroup
    sub: Felix
    group: Formal
  - fact_type: MemberOfDisjointGroup
    sub: Canus
    group: Formal

# Probabilistic facts
pfacts:
  - fact:
      fact_type: EquivalentTo
      sub: cat
      equivalent: Felix
    prob: 0.9
  - fact:
      fact_type: EquivalentTo
      sub: dog
      equivalent: Canus
    prob: 0.9
  - fact:
      fact_type: EquivalentTo
      sub: cat
      equivalent: Canus
    prob: 0.1  # Low probability - cats are not dogs!
```

### JSON Format

JSON provides machine-readable structured format, identical structure to YAML:

```json
{
  "name": "Family Relationships",
  "description": "Modeling family relationship types",
  "facts": [
    {
      "fact_type": "ProperSubClassOf",
      "sub": "Child",
      "sup": "Person"
    },
    {
      "fact_type": "ProperSubClassOf",
      "sub": "Parent",
      "sup": "Person"
    },
    {
      "fact_type": "DisjointWith",
      "sub": "Mother",
      "disjoint_with": "Father"
    }
  ],
  "pfacts": [
    {
      "fact": {
        "fact_type": "EquivalentTo",
        "sub": "Mom",
        "equivalent": "Mother"
      },
      "prob": 0.95
    },
    {
      "fact": {
        "fact_type": "EquivalentTo",
        "sub": "Dad",
        "equivalent": "Father"
      },
      "prob": 0.95
    }
  ]
}
```

### Python Module Format

Python modules can define knowledge bases programmatically:

```python
# my_kb.py
from boomer.model import KB, PFact, EquivalentTo, ProperSubClassOf

kb = KB(
    name="My Knowledge Base",
    description="Custom KB defined in Python",
    facts=[
        ProperSubClassOf("A", "B"),
        ProperSubClassOf("B", "C"),
    ],
    pfacts=[
        PFact(fact=EquivalentTo("X", "Y"), prob=0.8),
        PFact(fact=EquivalentTo("X", "Z"), prob=0.3),
    ]
)

# Can be loaded with:
# boomer-cli solve my_kb.py
# boomer-cli solve my_kb::kb
```

## Output Formats

### TSV Output

The TSV output format is designed for easy processing by downstream tools:

```tsv
# SSSOM-style metadata header
# name: Solution for Animal Taxonomy
# confidence: 0.9234
# combinations_explored: 1024
# satisfiable_combinations: 512
# time_elapsed: 0.234

# Tab-separated data
fact_type	arg1	arg2	truth_value	prior_prob	posterior_prob
EquivalentTo	cat	Felix	True	0.9	0.95
EquivalentTo	dog	Canus	True	0.9	0.94
EquivalentTo	cat	Canus	False	0.1	0.05
```

### JSON Solution Output

```json
{
  "confidence": 0.9234,
  "prior_prob": 0.81,
  "posterior_prob": 0.95,
  "number_of_combinations": 1024,
  "number_of_satisfiable_combinations": 512,
  "time_elapsed": 0.234,
  "solved_pfacts": [
    {
      "pfact": {
        "fact": {
          "fact_type": "EquivalentTo",
          "sub": "cat",
          "equivalent": "Felix"
        },
        "prob": 0.9
      },
      "truth_value": true,
      "posterior_prob": 0.95
    }
  ]
}
```

## Format Conversion

BOOMER provides easy conversion between formats:

```bash
# Convert PTable to YAML
boomer-cli convert input.ptable.tsv -o output.yaml

# Convert JSON to YAML
boomer-cli convert kb.json -o kb.yaml

# Convert Python module to JSON
boomer-cli convert boomer.datasets.animals -o animals.json

# Add metadata during conversion
boomer-cli convert input.tsv -o output.yaml \
  --name "My KB" \
  --description "Converted knowledge base"
```

### Python API for Conversion

```python
from boomer.io import load_kb, save_kb

# Load from any format (auto-detected)
kb = load_kb('input.ptable.tsv')
kb = load_kb('data.json')
kb = load_kb('data.yaml')

# Save to any format
save_kb(kb, 'output.json', format='json')
save_kb(kb, 'output.yaml', format='yaml')

# Note: PTable output not yet supported
# save_kb(kb, 'output.tsv', format='ptable')  # Not implemented
```

## Grid Search Configuration

Grid search uses YAML or JSON to specify parameter combinations:

```yaml
# grid_config.yaml
configurations:
  - {}  # Default configuration
configuration_matrix:
  max_pfacts_per_clique: [100, 150, 200]
  max_candidate_solutions: [100, 200]
  timeout_seconds: [2, 10]
  pr_filter: [0.2, 0.4, 0.6, 0.8]
```

Usage:
```bash
boomer-cli grid-search kb.yaml grid_config.yaml \
  --eval-kb-file gold.yaml \
  -o results.json
```

## Format Selection

BOOMER automatically detects formats based on file extensions, but you can explicitly specify formats when needed:

```bash
# Auto-detection (recommended)
boomer-cli solve data.json
boomer-cli solve data.yaml
boomer-cli solve data.ptable.tsv

# Explicit format specification
boomer-cli solve data -f json
boomer-cli solve data -f yaml
boomer-cli solve data.tsv -f ptable

# Output format specification
boomer-cli solve input.json -O yaml -o solution.yaml
boomer-cli solve input.yaml -O tsv -o solution.tsv
```

## Best Practices

1. **Use YAML/JSON for complex KBs** - When you have metadata, multiple fact types, or need version control
2. **Use PTable for simple mappings** - When you have straightforward probabilistic mappings
3. **Use Python modules for dynamic KBs** - When you need to generate facts programmatically
4. **Use TSV output for analysis** - Easy to import into spreadsheets or data analysis tools
5. **Use JSON/YAML output for integration** - Machine-readable formats for downstream processing

## Future: OWL Support

Future releases will support OWL (Web Ontology Language) for:
- Importing existing OWL ontologies
- Exporting BOOMER solutions to OWL format
- Integration with standard ontology tools
- Support for OWL axioms and annotations

This will enable BOOMER to work seamlessly with existing semantic web infrastructure and ontology management systems.