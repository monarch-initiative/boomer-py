# Ontology Conversion

BOOMER can import OBO and OWL ontology files directly, converting structural axioms into hard facts and cross-references/SKOS mappings into probabilistic facts suitable for reasoning.

## Quick Start

```bash
# Convert an OBO ontology to a boomer KB
pyboomer convert my_ontology.obo -o kb.yaml

# Convert an OWL ontology
pyboomer convert my_ontology.owl -o kb.yaml

# Solve directly from an ontology file
pyboomer solve my_ontology.obo -O markdown
```

## How It Works

The ontology converter reads an ontology file and produces a KB with two kinds of facts:

**Hard facts** (probability 1.0) from structural axioms:

- `is_a` / `SubClassOf` &rarr; `ProperSubClassOf`
- `equivalent_to` / `EquivalentClasses` &rarr; `EquivalentTo`
- `disjoint_from` / `DisjointClasses` &rarr; `DisjointWith`

**Probabilistic facts** from cross-references and mappings:

- `xref` / `oboInOwl:hasDbXref` &rarr; `EquivalentTo` (default prob 0.7)
- `skos:exactMatch` &rarr; `EquivalentTo` (default prob 0.9)
- `skos:closeMatch` &rarr; `EquivalentTo` (default prob 0.7)
- `skos:broadMatch` &rarr; `ProperSubClassOf` reversed (default prob 0.7)
- `skos:narrowMatch` &rarr; `ProperSubClassOf` (default prob 0.7)

**Disjoint groups** are auto-generated per ID prefix, so entities from different namespaces (e.g. `MONDO:` vs `ORDO:`) are placed in disjoint groups.

## Example: OBO Ontology

Given an OBO file with cross-references and SKOS mappings:

```obo
format-version: 1.4
ontology: disease-mappings

[Term]
id: MONDO:0001234
name: Alpha disease
is_a: MONDO:0000001 ! disease
xref: ORDO:123
property_value: skos:exactMatch OMIM:456789

[Term]
id: MONDO:0005678
name: Beta disease
is_a: MONDO:0000001 ! disease
xref: ORDO:456
property_value: skos:broadMatch ICD10:K72
```

Convert and solve:

```bash
# Convert to KB
pyboomer convert disease-mappings.obo -o disease.yaml

# Solve
pyboomer solve disease.yaml -O markdown
```

The converter produces:

- **Hard facts**: `MONDO:0001234 ProperSubClassOf MONDO:0000001`, etc.
- **Pfacts**: `MONDO:0001234 EquivalentTo ORDO:123` at 0.7, `MONDO:0001234 EquivalentTo OMIM:456789` at 0.9, `MONDO:0005678 ProperSubClassOf ICD10:K72` at 0.7 (broadMatch is reversed)
- **Disjoint groups**: one group per prefix (`MONDO`, `ORDO`, `OMIM`, `ICD10`)

## Configuration

### Python API

```python
from boomer.ontology_converter import OntologyConverterConfig, obo_to_kb

config = OntologyConverterConfig(
    # Xref probabilities
    xref_default_probability=0.5,
    xref_prefix_probabilities={"OMIM": 0.9, "ICD10": 0.6},

    # SKOS mapping probabilities
    skos_exact_match_prob=0.95,
    skos_close_match_prob=0.7,
    skos_broad_match_prob=0.7,
    skos_narrow_match_prob=0.7,

    # Filtering
    skip_obsolete=True,       # skip obsolete terms (default)
    include_xrefs=True,       # include xrefs as pfacts (default)
    include_skos=True,        # include SKOS mappings as pfacts (default)
    auto_disjoint_groups=True, # generate MemberOfDisjointGroup per prefix (default)
    min_probability=0.01,     # filter out very low probability pfacts
)
kb = obo_to_kb("my_ontology.obo", config=config)
```

### YAML Config File

```yaml
# ontology_config.yaml
xref_default_probability: 0.5
xref_prefix_probabilities:
  OMIM: 0.9
  ICD10: 0.6
  ORDO: 0.8
skos_exact_match_prob: 0.95
skip_obsolete: true
auto_disjoint_groups: true
```

```python
from boomer.ontology_converter import load_ontology_config, obo_to_kb

config = load_ontology_config("ontology_config.yaml")
kb = obo_to_kb("my_ontology.obo", config=config)
```

## OWL Support

The OWL backend uses [py-horned-owl](https://github.com/phillord/py-horned-owl) and supports multiple serializations:

- **OWL Functional Syntax** (`.ofn`)
- **OWL/XML** (`.owx`)
- **RDF/OWL** (`.owl`)

```bash
# Any OWL serialization works
pyboomer convert ontology.ofn -o kb.yaml
pyboomer convert ontology.owx -o kb.yaml
pyboomer convert ontology.owl -o kb.yaml
```

The same axiom types are extracted as for OBO. IRI-to-CURIE conversion uses the ontology's prefix declarations and handles OBO-style IRIs (e.g. `http://purl.obolibrary.org/obo/GO_0008150` &rarr; `GO:0008150`) automatically.

## Combining with Other Sources

You can merge ontology-derived KBs with SSSOM mappings or other KBs:

```bash
# Merge ontology structure with SSSOM mappings
pyboomer merge ontology.obo mappings.sssom.tsv -o combined.yaml

# Solve the merged KB
pyboomer solve combined.yaml -O markdown
```

## Seed-Based Extraction

For large ontologies, extract a neighborhood around entities of interest:

```bash
# Extract cluster around a specific entity
pyboomer extract ontology.obo --id MONDO:0001234 -o cluster.yaml

# Multiple seeds
pyboomer extract ontology.obo --id MONDO:0001234 --id ORDO:123 -o cluster.yaml

# Limit hop distance
pyboomer extract ontology.obo --id MONDO:0001234 --max-hops 2 -o cluster.yaml
```
