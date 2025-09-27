# Loaders API

The `boomer.loaders` module provides a unified interface for loading Knowledge Bases (KBs) from various sources including files and Python modules.

## Classes

### KBLoader

::: boomer.loaders.KBLoader

#### Methods

##### detect_format
::: boomer.loaders.KBLoader.detect_format

##### load_kb
::: boomer.loaders.KBLoader.load_kb

## Functions

### load_kb_smart

::: boomer.loaders.load_kb_smart

## Usage Examples

### Loading from Files

```python
from boomer.loaders import load_kb_smart

# Load with auto-detection
kb = load_kb_smart("data.ptable.tsv")
kb = load_kb_smart("data.json") 
kb = load_kb_smart("data.yaml")

# Load with explicit format
kb = load_kb_smart("data.tsv", format_name="ptable")
```

### Loading from Python Modules

```python
from boomer.loaders import load_kb_smart

# Load from dataset module (uses default 'kb' attribute)
kb = load_kb_smart("boomer.datasets.animals")

# Load with explicit attribute specification
kb = load_kb_smart("boomer.datasets.animals::kb")

# Load from custom attribute
kb = load_kb_smart("my.module::my_knowledge_base")

# Load with custom metadata
kb = load_kb_smart(
    "boomer.datasets.animals::kb", 
    name="Animal Classification",
    description="Example animal taxonomy KB"
)
```

### Format Detection

```python
from boomer.loaders import KBLoader

# Detect format automatically
fmt = KBLoader.detect_format("data.ptable.tsv")  # Returns "ptable"
fmt = KBLoader.detect_format("data.json")        # Returns "json"
fmt = KBLoader.detect_format("boomer.datasets.animals")  # Returns "py"
fmt = KBLoader.detect_format("boomer.datasets.animals::kb")  # Returns "py"
```

### Advanced Usage

```python
from boomer.loaders import KBLoader

# Use the loader class directly for more control
loader = KBLoader()

# Load with error handling
try:
    kb = loader.load_kb("my.module.path", "py")
except ImportError as e:
    print(f"Failed to import module: {e}")
except AttributeError as e:
    print(f"Module missing kb attribute: {e}")
```

## Supported Formats

| Format | Description | Examples |
|--------|-------------|----------|
| `ptable` | TSV probability tables | `data.ptable.tsv`, `data.tsv` |
| `json` | JSON knowledge base format | `data.json` |
| `yaml` | YAML knowledge base format | `data.yaml`, `data.yml` |
| `py` | Python module paths | `boomer.datasets.animals`, `my.module::custom_kb` |

## Format Detection Rules

The loader uses the following rules for automatic format detection:

1. **File extensions**: `.json`, `.yaml`, `.yml`, `.tsv`, `.py`
2. **Filename patterns**: Files containing "ptable" are treated as ptable format
3. **Python modules**: Dotted paths without file separators and without known extensions
4. **Attribute syntax**: Paths with `::` are treated as Python modules with explicit attributes
5. **Validation**: Python module paths must consist of valid Python identifiers

## Error Handling

The loader provides detailed error messages for common issues:

- **FileNotFoundError**: When input files don't exist
- **ImportError**: When Python modules cannot be imported
- **AttributeError**: When Python modules don't have a `kb` attribute
- **ValueError**: When formats cannot be detected or are unsupported
- **TypeError**: When module's `kb` attribute is not a KB instance