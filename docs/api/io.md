# IO API Reference

This page documents the input/output functions in BOOMER for loading and saving data.

## Probability Tables

### ptable_to_kb

```python
def ptable_to_kb(ptable: str, name: str = None, description: str = None, comments: str = None) -> KB:
    """
    Convert a probability table to a KB.
    
    The probability table is a TSV file with the following columns:
    1. subject ID
    2. object ID
    3. probability of subject SubClassOf object
    4. probability of object SubClassOf subject
    5. probability of subject EquivalentTo object
    6. probability of subject NotInSubsumptionWith object
    
    Each row generates four probabilistic facts, one for each relationship type.
    Additionally, each unique ID is assigned to a disjoint group based on its prefix.
    
    Args:
        ptable: Path to the probability table file
        name: Optional name for the KB
        description: Optional description for the KB
        comments: Optional comments for the KB
        
    Returns:
        A KB containing the facts from the probability table
    """
```

### ptable_to_pfacts

```python
def ptable_to_pfacts(ptable: str) -> Iterator[PFact]:
    """
    Convert a probability table to a list of PFacts.
    
    DEPRECATED: Use ptable_to_kb instead.
    
    This function is maintained for backward compatibility.
    
    Args:
        ptable: Path to the probability table file
        
    Yields:
        PFact objects derived from the probability table
    """
```

## JSON/YAML Serialization

### JSON Functions

#### kb_to_json

```python
def kb_to_json(kb: KB, indent: int = 2) -> str:
    """
    Serialize a KB to JSON string using Pydantic's built-in serialization.
    
    Args:
        kb: The knowledge base to serialize
        indent: JSON indentation level (default: 2)
        
    Returns:
        JSON string representation of the KB
    """
```

#### kb_from_json

```python
def kb_from_json(json_str: str) -> KB:
    """
    Deserialize a KB from JSON string using Pydantic's built-in deserialization.
    
    Args:
        json_str: JSON string representation of a KB
        
    Returns:
        KB instance
        
    Raises:
        ValueError: If the JSON is invalid or doesn't match KB schema
    """
```

### YAML Functions

#### kb_to_yaml

```python
def kb_to_yaml(kb: KB) -> str:
    """
    Serialize a KB to YAML string.
    
    Args:
        kb: The knowledge base to serialize
        
    Returns:
        YAML string representation of the KB
        
    Raises:
        ImportError: If PyYAML is not installed
    """
```

#### kb_from_yaml

```python
def kb_from_yaml(yaml_str: str) -> KB:
    """
    Deserialize a KB from YAML string.
    
    Args:
        yaml_str: YAML string representation of a KB
        
    Returns:
        KB instance
        
    Raises:
        ImportError: If PyYAML is not installed
        ValueError: If the YAML is invalid or doesn't match KB schema
    """
```

### File I/O Functions

#### save_kb

```python
def save_kb(kb: KB, file_path: Union[str, Path], format: str = "auto") -> None:
    """
    Save a KB to a file in JSON or YAML format.
    
    Args:
        kb: The knowledge base to save
        file_path: Path to the output file
        format: Format to use ("json", "yaml", or "auto" to detect from extension)
        
    Raises:
        ValueError: If format is unsupported
        ImportError: If PyYAML is required but not installed
    """
```

#### load_kb

```python
def load_kb(file_path: Union[str, Path], format: str = "auto") -> KB:
    """
    Load a KB from a JSON or YAML file.
    
    Args:
        file_path: Path to the input file
        format: Format to use ("json", "yaml", or "auto" to detect from extension)
        
    Returns:
        KB instance
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If format is unsupported or file content is invalid
        ImportError: If PyYAML is required but not installed
    """
```

## Utility Functions

### id_prefix

```python
def id_prefix(id: str) -> str:
    """
    Return the ID prefix of a given ID.
    
    Args:
        id: An identifier string (e.g., "MONDO:0000023")
        
    Returns:
        The prefix of the ID (e.g., "MONDO")
        
    Raises:
        ValueError: If the ID does not contain a prefix
    """
```

## Usage Examples

### Loading a KB from a Probability Table

```python
from boomer.io import ptable_to_kb
from boomer.search import solve

# Load a knowledge base from a probability table
kb = ptable_to_kb(
    "path/to/mapping.ptable.tsv",
    name="Disease Mappings",
    description="Mappings between MONDO and ICD10 terms"
)

# Print KB info
print(f"Loaded KB: {kb.name}")
print(f"Description: {kb.description}")
print(f"Facts: {len(kb.facts)}")
print(f"Probabilistic facts: {len(kb.pfacts)}")

# Solve the KB
solution = solve(kb)
```

### Using the Legacy ptable_to_pfacts Function

```python
from boomer.io import ptable_to_pfacts
from boomer.model import KB
from boomer.search import solve

# Load probabilistic facts from a probability table
pfacts = list(ptable_to_pfacts("path/to/mapping.ptable.tsv"))

# Create a KB from the facts
kb = KB(pfacts=pfacts)

# Solve the KB
solution = solve(kb)
```

### Extracting ID Prefixes

```python
from boomer.io import id_prefix

# Extract prefixes from IDs
mondo_prefix = id_prefix("MONDO:0000023")  # Returns "MONDO"
icd_prefix = id_prefix("ICD10:K72.0")      # Returns "ICD10"

# Use for disjoint group assignment
from boomer.model import MemberOfDisjointGroup

entity_id = "MONDO:0000023"
group = id_prefix(entity_id)
disjoint_fact = MemberOfDisjointGroup(sub=entity_id, group=group)
```

### JSON/YAML Serialization Examples

#### Saving and Loading KBs as JSON

```python
from boomer.io import save_kb, load_kb, kb_to_json, kb_from_json
from boomer.datasets.animals import kb

# Save to JSON file
save_kb(kb, "animals.json")

# Load from JSON file
loaded_kb = load_kb("animals.json")

# Or use string serialization
json_str = kb_to_json(kb, indent=2)
print(json_str)

# Deserialize from string
kb_restored = kb_from_json(json_str)
```

#### Working with YAML

```python
from boomer.io import save_kb, load_kb, kb_to_yaml, kb_from_yaml
from boomer.datasets.animals import kb

# Save to YAML file (auto-detected from extension)
save_kb(kb, "animals.yaml")

# Load from YAML file
loaded_kb = load_kb("animals.yaml")

# Or use string serialization
yaml_str = kb_to_yaml(kb)
print(yaml_str)

# Deserialize from string
kb_restored = kb_from_yaml(yaml_str)
```

#### Format Auto-Detection

```python
from boomer.io import save_kb, load_kb
from boomer.datasets.animals import kb

# Format is automatically detected from file extension
save_kb(kb, "my_kb.json")    # Saves as JSON
save_kb(kb, "my_kb.yaml")    # Saves as YAML
save_kb(kb, "my_kb.yml")     # Also saves as YAML

# Loading also auto-detects format
kb_json = load_kb("my_kb.json")
kb_yaml = load_kb("my_kb.yaml")

# You can also specify format explicitly
save_kb(kb, "my_file.txt", format="json")  # Forces JSON format
```

#### Error Handling

```python
from boomer.io import kb_from_json, kb_from_yaml

try:
    # This will raise ValueError due to invalid JSON
    kb = kb_from_json("invalid json")
except ValueError as e:
    print(f"JSON parsing failed: {e}")

try:
    # This will raise ImportError if PyYAML is not installed
    kb = kb_from_yaml("name: test")
except ImportError as e:
    print(f"YAML support not available: {e}")
```

## File Format Specifications

### Probability Table (PTable) Format

The PTable format is a tab-separated values (TSV) file with 6 columns:

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

### JSON Format

The JSON format provides a complete serialization of KB objects using Pydantic's built-in serialization. Each fact type includes a `fact_type` discriminator field for proper deserialization.

Example JSON structure:
```json
{
  "name": "Animals",
  "description": "An ontology alignment example",
  "comments": null,
  "facts": [
    {
      "fact_type": "ProperSubClassOf",
      "sub": "Felix",
      "sup": "Mammalia"
    },
    {
      "fact_type": "MemberOfDisjointGroup",
      "sub": "cat",
      "group": "Common"
    }
  ],
  "pfacts": [
    {
      "fact": {
        "fact_type": "EquivalentTo",
        "sub": "cat",
        "equivalent": "Felix"
      },
      "prob": 0.9
    }
  ],
  "hypotheses": [],
  "labels": {}
}
```

### YAML Format

The YAML format provides the same information as JSON but in a more human-readable format:

```yaml
name: Animals
description: An ontology alignment example
comments: null
facts:
- fact_type: ProperSubClassOf
  sub: Felix
  sup: Mammalia
- fact_type: MemberOfDisjointGroup
  sub: cat
  group: Common
pfacts:
- fact:
    fact_type: EquivalentTo
    sub: cat
    equivalent: Felix
  prob: 0.9
hypotheses: []
labels: {}
```

**Note**: YAML support requires the `pyyaml` package to be installed:
```bash
pip install pyyaml
```