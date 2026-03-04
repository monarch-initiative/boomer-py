"""
Knowledge Base loaders for different input formats.

This module provides a unified interface for loading KBs from various sources
including files (ptable, JSON, YAML) and Python modules.
"""

import importlib
from pathlib import Path
from typing import Optional, Union

from boomer.io import ptable_to_kb, load_kb as load_kb_file
from boomer.model import KB


class KBLoader:
    """Unified KB loader supporting multiple formats and sources."""
    
    SUPPORTED_FORMATS = ["ptable", "json", "yaml", "py", "obo", "owl", "sssom"]
    
    @classmethod
    def detect_format(cls, input_path: Union[str, Path]) -> str:
        """
        Auto-detect format from file extension or path.
        
        Args:
            input_path: Path to input file or module path
            
        Returns:
            Detected format string
            
        Raises:
            ValueError: If format cannot be detected
        """
        input_str = str(input_path)
        
        # Check for Python module path with attribute syntax (module::attribute)
        if "::" in input_str:
            module_part = input_str.split("::")[0]
            # Check if the module part looks like a Python module path
            if ("." in module_part and 
                "/" not in module_part and 
                "\\" not in module_part):
                parts = module_part.split(".")
                if all(part.replace("_", "").isalnum() and not part[0].isdigit() for part in parts if part):
                    return "py"
        
        # Convert to Path for file-based checks
        if isinstance(input_path, str):
            path_obj = Path(input_str)
        else:
            path_obj = input_path
            
        # Check file extensions first
        ext = path_obj.suffix.lower()
        if ".sssom." in path_obj.name.lower():
            return "sssom"
        if ext == ".tsv" or "ptable" in path_obj.name:
            return "ptable"
        elif ext == ".json":
            return "json"
        elif ext in [".yaml", ".yml"]:
            return "yaml"
        elif ext == ".py":
            return "py"
        elif ext == ".obo":
            return "obo"
        elif ext in [".owl", ".owx", ".ofn"]:
            return "owl"

        # Check for Python module path (contains dots, no path separators, not a known file extension)
        if ("." in input_str and 
            "/" not in input_str and 
            "\\" not in input_str and
            ext not in [".tsv", ".json", ".yaml", ".yml", ".py"]):
            # Split into parts and check if they look like Python identifiers
            parts = input_str.split(".")
            if all(part.replace("_", "").isalnum() and not part[0].isdigit() for part in parts if part):
                # Looks like valid Python module path
                return "py"
        
        # If we get here, format could not be detected
        raise ValueError(f"Cannot auto-detect format for '{input_path}'")
    
    @classmethod
    def load_kb(
        cls, 
        input_path: Union[str, Path], 
        format_name: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> KB:
        """
        Load a KB from the specified input source.
        
        Args:
            input_path: Path to file or Python module path
            format_name: Format override (auto-detected if None)
            name: Optional name for the KB
            description: Optional description for the KB
            
        Returns:
            Loaded KB instance
            
        Raises:
            ValueError: If format is unsupported
            ImportError: If Python module cannot be imported
            FileNotFoundError: If file does not exist
        """
        # Auto-detect format if not specified
        if format_name is None:
            format_name = cls.detect_format(input_path)
        
        # Validate format
        if format_name not in cls.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format_name}")
        
        # Load based on format
        if format_name == "ptable":
            return cls._load_ptable(input_path, name, description)
        elif format_name in ["json", "yaml"]:
            return cls._load_structured(input_path, format_name)
        elif format_name == "py":
            return cls._load_python_module(input_path, name, description)
        elif format_name in ["obo", "owl"]:
            return cls._load_ontology(input_path)
        elif format_name == "sssom":
            return cls._load_sssom(input_path)
        else:
            raise ValueError(f"Unsupported format: {format_name}")
    
    @classmethod
    def _load_ptable(cls, input_path: Union[str, Path], name: Optional[str], description: Optional[str]) -> KB:
        """Load KB from ptable format."""
        return ptable_to_kb(str(input_path), name=name, description=description)
    
    @classmethod
    def _load_structured(cls, input_path: Union[str, Path], format_name: str) -> KB:
        """Load KB from JSON or YAML format."""
        return load_kb_file(str(input_path), format_name)
    
    @classmethod
    def _load_ontology(cls, input_path: Union[str, Path]) -> KB:
        """Load KB from OBO or OWL ontology file."""
        from boomer.ontology_converter import ontology_to_kb
        return ontology_to_kb(input_path)

    @classmethod
    def _load_sssom(cls, input_path: Union[str, Path]) -> KB:
        """Load KB from SSSOM TSV file."""
        from boomer.sssom_converter import sssom_to_kb
        return sssom_to_kb(input_path)

    @classmethod
    def _load_python_module(cls, module_path: Union[str, Path], name: Optional[str], description: Optional[str]) -> KB:
        """
        Load KB from Python module.
        
        Args:
            module_path: Python module path, optionally with attribute specification
                        (e.g., 'boomer.datasets.animals' or 'boomer.datasets.animals::kb')
            name: Optional name override for the KB
            description: Optional description override for the KB
            
        Returns:
            KB instance from the module's specified or default 'kb' attribute
            
        Raises:
            ImportError: If module cannot be imported
            AttributeError: If module doesn't have the specified attribute
            TypeError: If the attribute is not a KB instance
        """
        module_spec = str(module_path)
        
        # Parse module and attribute specification
        if "::" in module_spec:
            module_name, attribute_name = module_spec.split("::", 1)
        else:
            module_name = module_spec
            attribute_name = "kb"  # Default attribute name
        
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise ImportError(f"Cannot import module '{module_name}': {e}")
        
        if not hasattr(module, attribute_name):
            raise AttributeError(f"Module '{module_name}' does not have a '{attribute_name}' attribute")
        
        kb = getattr(module, attribute_name)
        if not isinstance(kb, KB):
            raise TypeError(f"Module '{module_name}' {attribute_name} attribute is not a KB instance")
        
        # Create a copy and optionally override metadata
        if name is not None or description is not None:
            kb = kb.model_copy()
            if name is not None:
                kb.name = name
            if description is not None:
                kb.description = description
        
        return kb


def load_kb_smart(
    input_path: Union[str, Path], 
    format_name: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None
) -> KB:
    """
    Convenience function to load a KB with smart format detection.
    
    This is the recommended way to load KBs in CLI and other applications.
    
    Args:
        input_path: Path to file or Python module path
        format_name: Format override (auto-detected if None)
        name: Optional name for the KB
        description: Optional description for the KB
        
    Returns:
        Loaded KB instance
    """
    return KBLoader.load_kb(input_path, format_name, name, description)