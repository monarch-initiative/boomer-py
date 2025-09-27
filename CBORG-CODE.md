# BOOMER-PY Development Guidelines

## Jupyter Notebook Best Practices
- **Pre-execute notebooks**: Always execute notebooks before committing so cells show their outputs
- **Use papermill for execution**: `uv run papermill notebook.ipynb notebook.ipynb` to execute in place
  - Alternative: Use `make notebooks` or `just notebooks` to execute all notebooks
  - For tutorials only: `make tutorials` or `just tutorials`
- **Fix syntax before execution**: Ensure all model constructors use keyword arguments (e.g., `PFact(fact=..., prob=...)`)
- **Handle headers in data files**: When loading TSV/CSV files, skip header rows appropriately
- **Test execution**: Run a quick test to ensure all cells execute without errors before finalizing
- **Clean outputs if needed**: `make clean-notebooks` or `just clean-notebooks` to clear all cell outputs
- **Always use timeouts**: Configure `SearchConfig(timeout_seconds=60)` for all `solve()` calls in notebooks to prevent infinite execution
  - Create a `DEFAULT_CONFIG` at the beginning of notebooks for consistency
  - For complex problems, adjust timeout as needed but always set a reasonable limit
- **Note**: Some cells may take time to execute (especially search operations with large datasets)

## Build & Test Commands
- **Run all tests**: `make test` or `uv run pytest`
- **Run specific test**: `uv run pytest tests/test_search.py::test_solve_animals`
- **Run tests with name pattern**: `uv run pytest -k "animals"`
- **Run only doctests**: `make doctest`
- **Run linting**: `make lint` or `uv run ruff check src/`
- **Format code**: `make format` or `uv run ruff format src/`
- **Fix lint issues**: `make lint-fix` or `uv run ruff check --fix src/`

## CLI Commands

### Solve Command (Default)
Performs probabilistic reasoning on input knowledge bases.

**Supported input formats**:
- `ptable` - TSV probability tables
- `json` - JSON knowledge base format  
- `yaml` - YAML knowledge base format
- `py` - Python module paths (e.g., `boomer.datasets.animals`)

**Basic usage** (maintains backward compatibility):
```bash
uv run python -m boomer.cli input.ptable.tsv
uv run python -m boomer.cli solve input.ptable.tsv
```

**Input format examples**:
```bash
# Python module (format auto-detected)
uv run python -m boomer.cli solve boomer.datasets.animals

# Python module with explicit attribute
uv run python -m boomer.cli solve boomer.datasets.animals::kb

# Explicit format specification
uv run python -m boomer.cli solve boomer.datasets.animals -f py

# Mixed formats work with auto-detection
uv run python -m boomer.cli solve data.json
uv run python -m boomer.cli solve data.yaml
```

**Output formats**:
- **Markdown**: `uv run python -m boomer.cli solve input.ptable.tsv -O markdown`
- **TSV**: `uv run python -m boomer.cli solve input.ptable.tsv -O tsv -o output.tsv`
  - Format: `fact_type`, `arg1`, `arg2`, ..., `argN`, `truth_value`, `prior_probability`, `posterior_probability`
  - Columns automatically adjust to maximum arity of facts in the solution
  - Includes SSSOM-style YAML metadata header with search statistics
  - Use `--quiet` for pure TSV output without console summary
- **JSON**: `uv run python -m boomer.cli solve input.ptable.tsv -O json -o output.json`
- **YAML**: `uv run python -m boomer.cli solve input.ptable.tsv -O yaml -o output.yaml`

### Convert Command
Converts between different knowledge base formats.

**Supported input formats**:
- `ptable` - TSV probability tables
- `json` - JSON knowledge base format
- `yaml` - YAML knowledge base format
- `py` - Python module paths (e.g., `boomer.datasets.animals`)

**Supported output formats**:
- `json` - JSON knowledge base format
- `yaml` - YAML knowledge base format

**Usage examples**:
```bash
# Convert ptable to JSON (format auto-detected from extensions)
uv run python -m boomer.cli convert input.ptable.tsv -o output.json

# Convert Python module to YAML
uv run python -m boomer.cli convert boomer.datasets.animals -o animals.yaml

# Convert ptable to YAML with explicit formats
uv run python -m boomer.cli convert input.tsv -o output.yaml -f ptable -O yaml

# Convert JSON to YAML
uv run python -m boomer.cli convert kb.json -o kb.yaml

# Add metadata when converting
uv run python -m boomer.cli convert input.ptable.tsv -o output.json -n "My KB" -D "Description"
```

**Note**: Converting back to ptable format is not yet implemented. Use JSON or YAML for KB serialization.

### Merge Command
Merges multiple knowledge base files into a single KB.

**Supported input formats**: All formats listed above (ptable, json, yaml, py)

**Usage examples**:
```bash
# Merge multiple ptable files
uv run python -m boomer.cli merge file1.ptable.tsv file2.ptable.tsv -o merged.json

# Merge mixed formats (auto-detected)
uv run python -m boomer.cli merge data.json boomer.datasets.animals kb.yaml -o combined.json

# Merge with custom metadata
uv run python -m boomer.cli merge file1.json file2.yaml -o merged.yaml -n "Combined KB" -D "Merged from multiple sources"
```

## Code Style Guidelines
- **Python version**: Python 3.10+
- **Project conventions**:
  - Do _not_ refactor existing code unless specifically requested.
  - Do _not_ revert or undo prior changes unless specifically requested.
  - This is a Python 3.10+ project; feel free to use Python 3.10 idioms (e.g. PEP 604 unions).
- **Typing**: Use strict typing with annotations
- **Models**: Use pydantic models or dataclasses
- **Naming**: 
  - snake_case for functions and variables
  - PascalCase for classes
- **Imports**: Group by standard lib, third-party, local
- **Architecture**:
  - Abstract base classes in reasoners
  - Renderers for different output formats
  - Dataset modules for test data
- **Error handling**: Implicit in reasoning rather than try/except blocks

## Key Model Information
- **EntityIdentifier**: Just a string alias, not a class
- **Fact**: Union type of different fact classes (SubClassOf, DisjointWith, etc.)
- **partition_kb()**: Uses networkx.strongly_connected_components() for directed graphs to identify ontological cliques
- **Clique size limiting**: max_pfacts_per_clique parameter keeps only highest probability facts when cliques get too large
- **Doctests**: Include docstring tests in function documentation