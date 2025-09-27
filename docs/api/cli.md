# CLI API Reference

This page documents the command-line interface (CLI) for BOOMER.

::: boomer.cli

## Commands

### solve

The main command for running probabilistic reasoning on knowledge bases.

**Supported input formats:**
- `ptable` - TSV probability tables
- `json` - JSON knowledge base format  
- `yaml` - YAML knowledge base format
- `py` - Python module paths (e.g., `boomer.datasets.animals`)

**Example usage:**
```python
# Load from different sources
kb = load_kb_smart("data.ptable.tsv")
kb = load_kb_smart("boomer.datasets.animals")  
kb = load_kb_smart("data.json")
```

### convert

Convert between different KB formats.

**Supported conversions:**
- From: ptable, json, yaml, py
- To: json, yaml

### merge

Merge multiple KB files into a single knowledge base.

**Features:**
- Mixed format input support
- Automatic format detection
- Metadata merging

### eval

Evaluate predicted facts from a BOOMER Solution against a gold-standard KB.

**Supported KB input formats:** ptable, json, yaml, py  
**Supported solution input formats:** json, yaml

### grid-search

Perform a grid search over hyperparameters using a grid spec file.

**Supported KB input formats:** ptable, json, yaml, py  
**Supported grid spec formats:** json, yaml  
**Supported eval KB input formats:** ptable, json, yaml, py  
**Supported output formats:** json, yaml

## Utility Functions

### get_renderer

::: boomer.cli.get_renderer

### load_kb  

::: boomer.cli.load_kb

### write_output

::: boomer.cli.write_output

## Integration with Loaders

The CLI uses the unified loader system from `boomer.loaders` for consistent KB loading across all commands. This provides:

- **Smart format detection**: Automatically detects file formats from extensions and module paths
- **Unified error handling**: Consistent error messages across all commands  
- **Extensible architecture**: Easy to add new input formats

## Key Features

- **Multi-format support**: ptable, JSON, YAML files and Python modules
- **Format auto-detection**: No need to specify formats in most cases
- **Mixed format operations**: Can merge/convert between different formats seamlessly
- **Python module integration**: Direct access to programmatic knowledge bases
- **Comprehensive error handling**: Clear error messages for common issues

## See Also

- [Loaders API](loaders.md) - Detailed documentation of the KB loading system
- [CLI Guide](../cli.md) - User guide for command-line usage