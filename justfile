# Run full test suite (pytest + doctests)
test: test-python doctest

# Run pytest
test-python:
    uv run pytest

# Run doctests on all Python source files
doctest:
    find src -type f \( -name "*.rst" -o -name "*.md" -o -name "*.py" \) -print0 | xargs -0 uv run python -m doctest --option ELLIPSIS --option NORMALIZE_WHITESPACE

# Run ruff linter
lint:
    uv run ruff check src/

# Format code with ruff
format:
    uv run ruff format src/

# Fix lint issues
lint-fix:
    uv run ruff check --fix src/

# Execute all Jupyter notebooks in-place with papermill
notebooks:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Executing notebooks with papermill..."
    for notebook in $(find docs -name "*.ipynb" -type f | grep -v .ipynb_checkpoints | grep -v executed.ipynb); do
        echo "  Executing $notebook..."
        uv run papermill "$notebook" "$notebook" --cwd . || exit 1
    done
    echo "All notebooks executed successfully!"

# Execute a specific notebook in-place
notebook FILE:
    @echo "Executing {{FILE}}..."
    uv run papermill "{{FILE}}" "{{FILE}}" --cwd .
    @echo "Done!"

# Execute only tutorial notebooks
tutorials:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Executing tutorial notebooks..."
    for notebook in $(find docs/tutorial -name "*.ipynb" -type f | grep -v .ipynb_checkpoints | grep -v executed.ipynb); do
        echo "  Executing $notebook..."
        uv run papermill "$notebook" "$notebook" --cwd . || exit 1
    done
    echo "Tutorial notebooks executed successfully!"

# Clean notebook outputs (clear all cell outputs)
clean-notebooks:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Cleaning notebook outputs..."
    for notebook in $(find docs -name "*.ipynb" -type f | grep -v .ipynb_checkpoints); do
        echo "  Cleaning $notebook..."
        uv run jupyter nbconvert --clear-output --inplace "$notebook" || exit 1
    done
    echo "All notebook outputs cleaned!"

# List all notebooks
list-notebooks:
    @echo "Notebooks found:"
    @find docs -name "*.ipynb" -type f | grep -v .ipynb_checkpoints | sed 's/^/  /'