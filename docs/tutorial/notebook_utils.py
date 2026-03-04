"""Utilities for tutorial notebooks."""

from pathlib import Path

from IPython.display import Markdown


def show(path: str | Path, lang: str = "yaml") -> Markdown:
    """Display a file as a fenced code block.

    Args:
        path: Path to the file to display.
        lang: Syntax highlighting language (yaml, turtle, tsv, etc.).
    """
    p = Path(path)
    text = p.read_text()
    return Markdown(f"**`{p.name}`**\n\n```{lang}\n{text}```")
