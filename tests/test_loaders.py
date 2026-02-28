"""Tests for KB loaders module."""

import pytest
from pathlib import Path
from boomer.loaders import KBLoader, load_kb_smart
from boomer.model import KB


class TestKBLoader:
    """Test the KBLoader class."""
    
    def test_detect_format_python_module(self):
        """Test format detection for Python module paths."""
        assert KBLoader.detect_format("boomer.datasets.animals") == "py"
        assert KBLoader.detect_format("my.module.name") == "py"
        # Test with explicit attribute syntax
        assert KBLoader.detect_format("boomer.datasets.animals::kb") == "py"
        assert KBLoader.detect_format("my.module::custom_attr") == "py"
        # Single names without dots should raise an error
        with pytest.raises(ValueError):
            KBLoader.detect_format("simple")
        
    def test_detect_format_files(self):
        """Test format detection for file paths."""
        assert KBLoader.detect_format("data.json") == "json"
        assert KBLoader.detect_format("data.yaml") == "yaml"
        assert KBLoader.detect_format("data.yml") == "yaml"
        assert KBLoader.detect_format("data.tsv") == "ptable"
        assert KBLoader.detect_format("data.ptable.tsv") == "ptable"
        assert KBLoader.detect_format("data.py") == "py"
        
    def test_detect_format_paths(self):
        """Test format detection for file paths with directories."""
        assert KBLoader.detect_format("/path/to/data.json") == "json"
        assert KBLoader.detect_format("./relative/data.yaml") == "yaml"
        assert KBLoader.detect_format("../parent/data.ptable.tsv") == "ptable"
        
    def test_detect_format_unknown(self):
        """Test format detection for unknown extensions."""
        # Unknown extensions that don't look like Python identifiers should raise error
        with pytest.raises(ValueError, match="Cannot auto-detect format"):
            KBLoader.detect_format("file.123ext")  # contains digits
            
    def test_load_python_module(self):
        """Test loading KB from Python module."""
        kb = KBLoader.load_kb("boomer.datasets.animals", "py")
        assert isinstance(kb, KB)
        assert len(kb.facts) > 0
        assert len(kb.pfacts) > 0
        
    def test_load_python_module_with_metadata(self):
        """Test loading KB from Python module with custom metadata."""
        kb = KBLoader.load_kb(
            "boomer.datasets.animals", 
            "py", 
            name="Custom Name", 
            description="Custom Description"
        )
        assert isinstance(kb, KB)
        assert kb.name == "Custom Name"
        assert kb.description == "Custom Description"
        
    def test_load_python_module_explicit_attribute(self):
        """Test loading KB from Python module with explicit attribute."""
        # Test with explicit kb attribute (should be same as default)
        kb1 = KBLoader.load_kb("boomer.datasets.animals::kb", "py")
        kb2 = KBLoader.load_kb("boomer.datasets.animals", "py")
        
        assert isinstance(kb1, KB)
        assert isinstance(kb2, KB)
        assert len(kb1.facts) == len(kb2.facts)
        assert len(kb1.pfacts) == len(kb2.pfacts)
        
    def test_load_python_module_nonexistent_attribute(self):
        """Test loading Python module with non-existent attribute."""
        with pytest.raises(AttributeError, match="does not have a 'nonexistent' attribute"):
            KBLoader.load_kb("boomer.datasets.animals::nonexistent", "py")
            
    def test_load_python_module_attribute_syntax_validation(self):
        """Test that attribute syntax is properly validated."""
        # Test various attribute syntax patterns
        kb = KBLoader.load_kb("boomer.datasets.animals::kb", "py")
        assert isinstance(kb, KB)
        
        # Test that module part is still validated
        with pytest.raises(ImportError):
            KBLoader.load_kb("nonexistent.module::kb", "py")
        
    def test_load_python_module_invalid(self):
        """Test loading invalid Python module."""
        with pytest.raises(ImportError):
            KBLoader.load_kb("nonexistent.module", "py")
            
    def test_load_python_module_no_kb(self):
        """Test loading Python module without kb attribute."""
        with pytest.raises(AttributeError, match="does not have a 'kb' attribute"):
            KBLoader.load_kb("boomer.io", "py")  # This module doesn't have kb
            
    def test_supported_formats(self):
        """Test that all supported formats are listed."""
        expected = {"ptable", "json", "yaml", "py", "obo", "owl", "sssom"}
        assert set(KBLoader.SUPPORTED_FORMATS) == expected


class TestLoadKBSmart:
    """Test the convenience function."""
    
    def test_load_kb_smart_python_module(self):
        """Test smart loading of Python module."""
        kb = load_kb_smart("boomer.datasets.animals")
        assert isinstance(kb, KB)
        assert len(kb.facts) > 0
        
    def test_load_kb_smart_python_module_explicit_attribute(self):
        """Test smart loading of Python module with explicit attribute."""
        kb = load_kb_smart("boomer.datasets.animals::kb")
        assert isinstance(kb, KB)
        assert len(kb.facts) > 0
        
    def test_load_kb_smart_format_override(self):
        """Test smart loading with format override."""
        kb = load_kb_smart("boomer.datasets.animals", format_name="py")
        assert isinstance(kb, KB)
        
    def test_load_kb_smart_format_override_with_attribute(self):
        """Test smart loading with format override and explicit attribute."""
        kb = load_kb_smart("boomer.datasets.animals::kb", format_name="py")
        assert isinstance(kb, KB)
        
    def test_load_kb_smart_invalid_format(self):
        """Test smart loading with invalid format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            load_kb_smart("test", format_name="invalid")