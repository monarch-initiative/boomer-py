from pathlib import Path
from typing import Iterator, Union

try:
    import yaml
except ImportError:
    yaml = None

from boomer.model import (
    KB,
    PFact,
    EquivalentTo,
    NotInSubsumptionWith,
    ProperSubClassOf,
    MemberOfDisjointGroup,
)


def id_prefix(id: str) -> str:
    """
    Return the ID prefix of a given ID.
    """
    toks = id.split(":")
    if len(toks) < 2:
        raise ValueError(f"Invalid ID: {id}")
    return toks[0]


def ptable_to_kb(
    ptable: str,
    name: str = None,
    description: str = None,
    comments: str = None,
    min_prob_NotInSubsumptionWith: float = 0.5,
) -> KB:
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
    # If name not provided, derive it from the filename
    if name is None:
        import os

        base_name = os.path.basename(ptable)
        name = os.path.splitext(base_name)[0]

    pfacts = []
    facts = []
    ids = set()

    with open(ptable, "r") as f:
        first_line = True
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Skip header line
            if first_line:
                first_line = False
                if line.startswith("subject") or "P(" in line:
                    continue

            parts = line.split("\t")
            if len(parts) != 6:
                raise ValueError(f"Invalid line in probability table: {line}")

            s, o, pr1, pr2, pr3, pr4 = parts
            ids.add(s)
            ids.add(o)
            pfacts.append(PFact(fact=ProperSubClassOf(sub=s, sup=o), prob=float(pr1)))
            pfacts.append(PFact(fact=ProperSubClassOf(sub=o, sup=s), prob=float(pr2)))
            pfacts.append(
                PFact(fact=EquivalentTo(sub=s, equivalent=o), prob=float(pr3))
            )
            if float(pr4) >= min_prob_NotInSubsumptionWith:
                pfacts.append(
                    PFact(fact=NotInSubsumptionWith(sub=s, sibling=o), prob=float(pr4))
                )

    # Add disjoint group memberships as facts, not pfacts
    # Only add if IDs have prefixes (e.g., "MONDO:123")
    for id in ids:
        try:
            prefix = id_prefix(id)
            facts.append(MemberOfDisjointGroup(sub=id, group=prefix))
        except ValueError:
            # Skip IDs without prefixes
            pass

    return KB(
        facts=facts,
        pfacts=pfacts,
        name=name,
        description=description,
        comments=comments,
    )


def ptable_to_pfacts(ptable: str) -> Iterator[PFact]:
    """
    Convert a probability table to a list of PFacts.

    DEPRECATED: Use ptable_to_kb instead.

    This function is maintained for backward compatibility.
    """
    kb = ptable_to_kb(ptable)

    # First yield all probabilistic facts
    for pfact in kb.pfacts:
        yield pfact

    # Then yield disjoint group memberships as PFacts with probability 1.0
    for fact in kb.facts:
        if isinstance(fact, MemberOfDisjointGroup):
            yield PFact(fact=fact, prob=1.0)


# JSON serialization functions


def kb_to_json(kb: KB, indent: int = 2) -> str:
    """
    Serialize a KB to JSON string using Pydantic's built-in serialization.

    Args:
        kb: The knowledge base to serialize
        indent: JSON indentation level (default: 2)

    Returns:
        JSON string representation of the KB
    """
    return kb.model_dump_json(indent=indent)


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
    try:
        return KB.model_validate_json(json_str)
    except Exception as e:
        raise ValueError(f"Failed to parse KB from JSON: {e}")


# YAML serialization functions


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
    if yaml is None:
        raise ImportError(
            "PyYAML is required for YAML serialization. Install with: pip install pyyaml"
        )

    # Convert to dict using Pydantic, excluding only None values
    kb_dict = kb.model_dump(exclude_none=True)

    # Create ordered dict with fields in model definition order
    ordered_dict = {}

    # Define the desired field order based on the KB model
    field_order = [
        'name', 'description', 'comments',
        'facts', 'pfacts', 'hypotheses',
        'labels', 'hyperparams', 'pfacts_entailed',
        'default_configurations'
    ]

    # Add fields in the defined order if they exist
    for field in field_order:
        if field in kb_dict:
            ordered_dict[field] = kb_dict[field]

    # Add any remaining fields that weren't in our predefined order
    for key, value in kb_dict.items():
        if key not in ordered_dict:
            ordered_dict[key] = value

    return yaml.dump(ordered_dict, default_flow_style=False, sort_keys=False)


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
    if yaml is None:
        raise ImportError(
            "PyYAML is required for YAML deserialization. Install with: pip install pyyaml"
        )

    try:
        kb_dict = yaml.safe_load(yaml_str)
        return KB.model_validate(kb_dict)
    except Exception as e:
        raise ValueError(f"Failed to parse KB from YAML: {e}")


# File I/O convenience functions


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
    file_path = Path(file_path)

    # Auto-detect format from file extension
    if format == "auto":
        ext = file_path.suffix.lower()
        if ext == ".json":
            format = "json"
        elif ext in [".yaml", ".yml"]:
            format = "yaml"
        else:
            raise ValueError(
                f"Cannot auto-detect format from extension '{ext}'. Use .json, .yaml, or .yml"
            )

    # Serialize based on format
    if format == "json":
        content = kb_to_json(kb)
    elif format == "yaml":
        content = kb_to_yaml(kb)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'yaml'")

    # Write to file
    file_path.write_text(content, encoding="utf-8")


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
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Auto-detect format from file extension
    if format == "auto":
        ext = file_path.suffix.lower()
        if ext == ".json":
            format = "json"
        elif ext in [".yaml", ".yml"]:
            format = "yaml"
        else:
            raise ValueError(
                f"Cannot auto-detect format from extension '{ext}'. Use .json, .yaml, or .yml"
            )

    # Read file content
    content = file_path.read_text(encoding="utf-8")

    # Deserialize based on format
    if format == "json":
        return kb_from_json(content)
    elif format == "yaml":
        return kb_from_yaml(content)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'yaml'")
