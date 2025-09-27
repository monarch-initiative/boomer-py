MAKEFLAGS += --warn-undefined-variables
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := test
.DELETE_ON_ERROR:
.SUFFIXES:
.SECONDARY:

RUN = uv run

# basename of a YAML file in model/
.PHONY: all clean

all: test


test: test-python doctest
test-python:
	$(RUN) pytest

DOCTEST_DIR = src
doctest:
	find $(DOCTEST_DIR) -type f \( -name "*.rst" -o -name "*.md" -o -name "*.py" \) -print0 | xargs -0 $(RUN) python -m doctest --option ELLIPSIS --option NORMALIZE_WHITESPACE

# Ruff formatting and linting
lint:
	$(RUN) ruff check src/

format:
	$(RUN) ruff format src/

lint-fix:
	$(RUN) ruff check --fix src/

# Execute all Jupyter notebooks in-place with papermill
notebooks:
	@echo "Executing notebooks with papermill..."
	@for notebook in $$(find docs -name "*.ipynb" -type f | grep -v .ipynb_checkpoints | grep -v executed.ipynb); do \
		echo "  Executing $$notebook..."; \
		$(RUN) papermill "$$notebook" "$$notebook" --cwd . || exit 1; \
	done
	@echo "All notebooks executed successfully!"

# Execute only tutorial notebooks
tutorials:
	@echo "Executing tutorial notebooks..."
	@for notebook in $$(find docs/tutorial -name "*.ipynb" -type f | grep -v .ipynb_checkpoints | grep -v executed.ipynb); do \
		echo "  Executing $$notebook..."; \
		$(RUN) papermill "$$notebook" "$$notebook" --cwd . || exit 1; \
	done
	@echo "Tutorial notebooks executed successfully!"

# Clean notebook outputs (clear all cell outputs)
clean-notebooks:
	@echo "Cleaning notebook outputs..."
	@for notebook in $$(find docs -name "*.ipynb" -type f | grep -v .ipynb_checkpoints); do \
		echo "  Cleaning $$notebook..."; \
		$(RUN) jupyter nbconvert --clear-output --inplace "$$notebook" || exit 1; \
	done
	@echo "All notebook outputs cleaned!"
