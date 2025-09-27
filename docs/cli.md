# BOOMER Command Line Interface

BOOMER provides a command-line interface (CLI) that allows you to run probabilistic reasoning on various input formats, including Probability Tables (PTables), JSON/YAML knowledge bases, and Python dataset modules.

## Installation

### For Users

Once BOOMER is published to PyPI, you can install it using pip or uvx:

```bash
# Using pip
pip install boomer

# Or using uvx for isolated execution
uvx boomer-cli --help
```

### For Developers

Developers should use the modern `uv` workflow:

```bash
# Clone and set up for development
git clone https://github.com/cmungall/boomer-py.git
cd boomer-py
uv sync

# Run CLI during development
uv run boomer-cli --help
```

## Basic Usage

The BOOMER CLI uses the `boomer-cli` command with subcommands for different operations:

```bash
boomer-cli [COMMAND] [OPTIONS] [ARGS]
```

Available commands:
- `solve` (default) - Run probabilistic reasoning on input
- `convert` - Convert between knowledge base formats
- `merge` - Merge multiple knowledge bases
- `extract` - Extract a subset of facts from a knowledge base
- `eval` - Evaluate predictions against gold standard
- `grid-search` - Perform hyperparameter grid search

BOOMER supports multiple input formats with automatic format detection:
- **PTable files**: `.ptable.tsv`, `.tsv` files
- **JSON/YAML**: `.json`, `.yaml`, `.yml` files  
- **Python modules**: Dotted module paths like `boomer.datasets.animals`

By default, BOOMER outputs results in Markdown format to stdout.

### Examples

#### CLI Examples

```bash
# Process a PTable file (solve is the default command)
boomer-cli tests/input/MONDO_0000023.ptable.tsv

# Explicitly use solve command
boomer-cli solve tests/input/MONDO_0000023.ptable.tsv

# Process a Python dataset module
boomer-cli solve boomer.datasets.animals

# Process JSON/YAML files
boomer-cli solve data.json
boomer-cli solve data.yaml

# Save output to a file in different formats
boomer-cli solve tests/input/MONDO_0000023.ptable.tsv -o results.md
boomer-cli solve data.json -O tsv -o results.tsv
boomer-cli solve data.yaml -O json -o solution.json

# Explicit format specification (usually not needed)
boomer-cli solve boomer.datasets.animals --format py

# Filter high-confidence results
boomer-cli solve mapping.ptable.tsv --threshold 0.9 -o high_conf.md
```

#### Python API Examples

```python
from boomer.io import ptable_to_kb, kb_to_ptable
from boomer.search import solve
from boomer.model import KB

# Load a knowledge base from a PTable file
with open('mapping.ptable.tsv') as f:
    kb = ptable_to_kb(f)

# Solve the knowledge base
solution = solve(kb, max_solutions=100)

# Access results
for fact, prob in solution.posterior_probabilities.items():
    if prob > 0.8:
        print(f"{fact}: {prob:.3f}")
```

## Solve Command Options

```
Usage: boomer-cli solve [OPTIONS] INPUT_FILE_OR_MODULE

  Run probabilistic reasoning on input knowledge bases.
  Supports ptable, json, yaml files and Python module paths.

Options:
  -f, --format [ptable|json|yaml|py]  Input format (auto-detected if not specified)
  -n, --name TEXT                     Name for the knowledge base
  -D, --description TEXT              Description for the knowledge base
  -i, --max-iterations INTEGER        Maximum number of iterations
  -s, --max-solutions INTEGER         Maximum number of candidate solutions
  -t, --timeout FLOAT                 Maximum time in seconds to run the search
  -C, --max-pfacts-per-clique INTEGER Maximum probabilistic facts per clique
  -o, --output PATH                   Output file (defaults to stdout)
  -O, --format-output [markdown|tsv|json|yaml]
                                      Output format (default: markdown)
  -d, --output-dir PATH               Output directory for intermediate solutions
  -T, --threshold FLOAT               Posterior probability threshold (default: 0.8)
  -q, --quiet                         Suppress progress output
  -v, --verbose                       Verbose output (use -vv for debug)
  -h, --help                          Show this message and exit.
```

## Example Workflow

### 1. Running with Default Settings

```bash
# CLI usage
boomer-cli tests/input/MONDO_0000023.ptable.tsv

# Or explicitly using solve command
boomer-cli solve tests/input/MONDO_0000023.ptable.tsv

# Python API equivalent
from boomer.io import ptable_to_kb
from boomer.search import solve

with open('tests/input/MONDO_0000023.ptable.tsv') as f:
    kb = ptable_to_kb(f)
solution = solve(kb)
```

This will:
- Load the PTable file
- Run the search with default settings
- Print a summary and the full solution to stdout

### 2. Customizing the Search

```bash
# CLI usage
boomer-cli solve tests/input/MONDO_0000023.ptable.tsv \
  --name "Acute Liver Failure" \
  --description "Mapping between MONDO, ORDO, and ICD10 codes" \
  --max-solutions 100 \
  --timeout 30

# Python API equivalent
from boomer.io import ptable_to_kb
from boomer.search import solve

with open('tests/input/MONDO_0000023.ptable.tsv') as f:
    kb = ptable_to_kb(f)
    kb.name = "Acute Liver Failure"
    kb.description = "Mapping between MONDO, ORDO, and ICD10 codes"

solution = solve(kb, max_solutions=100, timeout=30)
```

This will:
- Load the PTable file with a custom name and description
- Limit the search to 100 candidate solutions
- Set a 30-second timeout for the search

### 3. Filtering Results and Saving Output

```bash
# CLI usage - Markdown output
boomer-cli solve tests/input/MONDO_0000023.ptable.tsv \
  --threshold 0.95 \
  --output high_confidence_mappings.md

# TSV output for downstream processing
boomer-cli solve tests/input/MONDO_0000023.ptable.tsv \
  --threshold 0.95 \
  -O tsv \
  -o high_confidence.tsv

# JSON output for programmatic consumption
boomer-cli solve tests/input/MONDO_0000023.ptable.tsv \
  --threshold 0.95 \
  -O json \
  -o solution.json

# Python API equivalent
from boomer.io import ptable_to_kb
from boomer.search import solve
from boomer.renderers import MarkdownRenderer

with open('tests/input/MONDO_0000023.ptable.tsv') as f:
    kb = ptable_to_kb(f)
solution = solve(kb)

# Filter high confidence results
renderer = MarkdownRenderer(threshold=0.95)
with open('high_confidence_mappings.md', 'w') as out:
    out.write(renderer.render(solution, kb))
```

This will:
- Load the PTable file
- Only report results with posterior probability >= 0.95
- Save the full solution to high_confidence_mappings.md
- Print a summary to stdout

## Additional Commands

### Convert Command

Convert between different KB formats:

```bash
# Convert ptable to JSON
boomer-cli convert input.ptable.tsv -o output.json

# Convert Python module to YAML
boomer-cli convert boomer.datasets.animals -o animals.yaml

# Convert JSON to YAML
boomer-cli convert kb.json -o kb.yaml

# Convert with custom metadata
boomer-cli convert input.ptable.tsv -o output.json -n "My KB" -D "Description"

# Explicit format specification
boomer-cli convert input.tsv -f ptable -O yaml -o output.yaml
```

**Python API equivalent:**
```python
from boomer.io import ptable_to_kb, save_kb

# Load and convert
with open('input.ptable.tsv') as f:
    kb = ptable_to_kb(f)
    kb.name = "My KB"
    kb.description = "Description"

# Save as JSON
save_kb(kb, 'output.json', format='json')

# Save as YAML
save_kb(kb, 'output.yaml', format='yaml')
```

**Supported input formats**: ptable, json, yaml, py  
**Supported output formats**: json, yaml

### Merge Command

Merge multiple KB files into a single KB:

```bash
# Merge multiple ptable files
boomer-cli merge file1.ptable.tsv file2.ptable.tsv -o merged.json

# Merge mixed formats (auto-detected)
boomer-cli merge data.json boomer.datasets.animals kb.yaml -o combined.json

# Merge with custom metadata
boomer-cli merge file1.json file2.yaml -o merged.yaml -n "Combined KB" -D "Merged sources"

# Merge and output as YAML
boomer-cli merge file1.json file2.json file3.json -O yaml -o merged.yaml
```

**Python API equivalent:**
```python
from boomer.io import load_kb, save_kb
from boomer.model import KB, merge_kbs

# Load multiple KBs
kb1 = load_kb('file1.json')
kb2 = load_kb('file2.yaml')
kb3 = load_kb('file3.ptable.tsv')

# Merge them
merged_kb = merge_kbs([kb1, kb2, kb3])
merged_kb.name = "Combined KB"
merged_kb.description = "Merged sources"

# Save the result
save_kb(merged_kb, 'merged.json', format='json')
```

### Extract Command

Extract a subset of facts from a knowledge base based on entity IDs:

```bash
# Extract facts for specific entities (IDs in text file, one per line)
boomer-cli extract kb.json entity_ids.txt -o subset.json

# Extract from ptable format
boomer-cli extract full.ptable.tsv ids.txt -o subset.ptable.tsv

# Extract from Python module
boomer-cli extract boomer.datasets.animals ids.txt -o animal_subset.yaml

# Explicit format specification
boomer-cli extract kb.data -f json ids.txt -O yaml -o subset.yaml
```

**Python API equivalent:**
```python
from boomer.io import load_kb, save_kb
from boomer.model import extract_subset

# Load KB and entity IDs
kb = load_kb('kb.json')
with open('entity_ids.txt') as f:
    entity_ids = [line.strip() for line in f]

# Extract subset
subset_kb = extract_subset(kb, entity_ids)

# Save the subset
save_kb(subset_kb, 'subset.json', format='json')
```

### Eval Command

Evaluate predicted facts from a BOOMER Solution against a gold-standard KB:

```bash
# Compare gold facts in a KB against a solution file
boomer-cli eval gold_kb.yaml solution.json -o evaluation.json

# Auto-detect formats from extensions
boomer-cli eval gold.ptable.tsv solution.yaml -o results.yaml

# Explicit formats
boomer-cli eval gold.pb solution.json --kb-format ptable --solution-format json -o eval.json

# Output evaluation metrics as YAML
boomer-cli eval gold_kb.json solution.json -O yaml -o metrics.yaml
```

**Python API equivalent:**
```python
from boomer.io import load_kb, load_solution
from boomer.eval import evaluate_solution

# Load gold standard and solution
gold_kb = load_kb('gold_kb.yaml')
solution = load_solution('solution.json')

# Evaluate
metrics = evaluate_solution(solution, gold_kb)
print(f"Precision: {metrics.precision:.3f}")
print(f"Recall: {metrics.recall:.3f}")
print(f"F1 Score: {metrics.f1:.3f}")
```

**Supported KB input formats**: ptable, json, yaml, py  
**Supported solution input formats**: json, yaml

### Grid Search Command

Perform a hyperparameter grid search using a JSON/YAML grid specification:

```bash
# Run grid search with evaluation against gold standard
boomer-cli grid-search data.yaml grid_spec.json \
    --eval-kb-file gold.yaml \
    -o grid_results.json

# Auto-detect formats, YAML output
boomer-cli grid-search data.ptable.tsv grid_spec.yaml \
    -e gold.ptable.tsv -O yaml -o results.yml

# Grid search without evaluation (just solve with different params)
boomer-cli grid-search kb.json params.yaml -o search_results.json
```

**Example grid specification (grid_spec.yaml):**
```yaml
parameters:
  max_solutions:
    - 10
    - 50
    - 100
  max_pfacts_per_clique:
    - 5
    - 10
    - 20
  timeout:
    - 30
    - 60
```

**Python API equivalent:**
```python
from boomer.grid_search import grid_search
from boomer.io import load_kb
import yaml

# Load KB and grid spec
kb = load_kb('data.yaml')
with open('grid_spec.yaml') as f:
    grid_spec = yaml.safe_load(f)

# Optional: load gold standard for evaluation
gold_kb = load_kb('gold.yaml')

# Run grid search
results = grid_search(kb, grid_spec, eval_kb=gold_kb)

# Process results
for params, metrics in results:
    print(f"Params: {params}")
    print(f"F1 Score: {metrics.f1:.3f}\n")
```

**Supported KB formats**: ptable, json, yaml, py  
**Supported grid spec formats**: json, yaml  
**Supported eval KB formats**: ptable, json, yaml, py  
**Supported output formats**: json, yaml

## Python Module Support

BOOMER can load knowledge bases directly from Python modules. This is useful for:

- Built-in dataset modules (e.g., `boomer.datasets.animals`)
- Custom KB modules in your project
- Programmatically generated KBs

**Requirements for Python modules**:
- Module must have a `kb` attribute (or custom attribute specified with `::`)
- Module path must use valid Python identifiers
- Module must be importable from the current environment

**Attribute Specification**:
By default, BOOMER looks for a `kb` attribute in the module. You can specify a custom attribute using the `::` syntax:

```bash
# Use default 'kb' attribute
boomer solve boomer.datasets.animals

# Explicit 'kb' attribute (same as above)
boomer solve boomer.datasets.animals::kb

# Use custom attribute name
boomer solve my_project.models::my_knowledge_base
```

**CLI Examples**:
```bash
# Use built-in datasets
boomer-cli solve boomer.datasets.animals
boomer-cli solve boomer.datasets.family
boomer-cli solve boomer.datasets.quad

# Use explicit attribute specification
boomer-cli solve boomer.datasets.animals::kb
boomer-cli convert boomer.datasets.family::kb -o family.json

# Use custom modules with custom attributes
boomer-cli solve my_project.knowledge_bases.taxonomy::main_kb
boomer-cli convert custom.kb.module::specialized_kb -o exported.json

# Process and save in different formats
boomer-cli solve boomer.datasets.animals -O tsv -o animals_solution.tsv
boomer-cli solve boomer.datasets.family -O json -o family_solution.json
```

**Python API Examples**:
```python
# Import built-in datasets directly
from boomer.datasets import animals, family
from boomer.search import solve

# Use the KB directly
solution = solve(animals.kb)

# Or load dynamically
import importlib
module = importlib.import_module('boomer.datasets.animals')
kb = getattr(module, 'kb')
solution = solve(kb)
```

## Troubleshooting

If you encounter issues with the CLI, try the following:

1. Check that your input file is properly formatted
2. Use the `--quiet` flag to reduce output if the results are too verbose
3. Increase the `--timeout` if your search is not completing