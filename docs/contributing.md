# Contributing to BOOMER

Thank you for your interest in contributing to BOOMER! This document provides guidelines and information about how to contribute to the project.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- Basic understanding of probabilistic reasoning and ontologies

### Setting Up Your Development Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/cmungall/boomer-py.git
   cd boomer-py
   ```

2. **Create a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests to verify your setup**:
   ```bash
   make test
   ```

## Development Workflow

### Making Changes

1. **Create a new branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** to the codebase.

3. **Run the linter** to ensure code quality:
   ```bash
   make lint
   ```

4. **Run tests** to ensure your changes don't break existing functionality:
   ```bash
   make test
   ```

5. **Commit your changes** with a clear commit message:
   ```bash
   git commit -m "Add feature: your feature description"
   ```

6. **Push your changes** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Submit a pull request** to the main repository.

### Code Style

- Follow Python's [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide.
- Use type annotations for function parameters and return values.
- Write docstrings for all functions, classes, and methods.
- Use descriptive variable names and comments where necessary.
- Aim for clean, readable, and maintainable code.

### Testing

- Write tests for all new functionality.
- Update existing tests when modifying functionality.
- Use pytest for testing.
- Aim for high test coverage.

## Project Structure

- `src/boomer/`: Core source code
  - `model.py`: Data models
  - `search.py`: Search algorithms
  - `reasoners/`: Reasoning implementations
  - `renderers/`: Output rendering
  - `io.py`: Input/output utilities
  - `cli.py`: Command-line interface
- `tests/`: Test files
- `docs/`: Documentation
- `Makefile`: Build and test commands

## Adding Features

### New Fact Types

To add a new type of fact:

1. Define the fact class in `src/boomer/model.py`.
2. Update the `Fact` union type.
3. Update the reasoners to handle the new fact type.
4. Add tests for the new fact type.

### New Reasoners

To add a new reasoner:

1. Create a new file in the `src/boomer/reasoners/` directory.
2. Implement the `Reasoner` interface.
3. Add tests for the new reasoner.
4. Update documentation.

### New Input/Output Formats

To add a new input or output format:

1. Add functions to `src/boomer/io.py`.
2. Add appropriate renderer in `src/boomer/renderers/`.
3. Update the CLI to support the new format.
4. Add tests and documentation.

## Documentation

- Update documentation when adding or changing features.
- Add examples for new functionality.
- Use Markdown for documentation.
- Build and test documentation using MkDocs:
  ```bash
  mkdocs serve  # Serves docs locally
  mkdocs build  # Builds static site
  ```

## Submitting a Pull Request

1. Ensure your code passes all tests and linting.
2. Update documentation if necessary.
3. Submit a pull request with a clear description of the changes.
4. Wait for review and address any feedback.

## Release Process

1. Update version number in `pyproject.toml`.
2. Update CHANGELOG.md with details of changes.
3. Create a new release on GitHub.
4. Build and publish the package to PyPI.

## Getting Help

If you have questions or need help, you can:

- Open an issue on GitHub
- Contact the project maintainer

Thank you for contributing to BOOMER!