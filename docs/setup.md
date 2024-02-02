# Setting Up a Python Virtual Environment Using Poetry and Pyenv

To streamline the development process and ensure consistency across environments, we use Poetry for dependency management and Pyenv for Python version management. Here's how to set up your development environment:

## Prerequisites

- **Pyenv**: Manages multiple Python versions. [Install Pyenv](https://github.com/pyenv/pyenv#installation).
- **Poetry**: Manages dependencies and virtual environments. [Install Poetry](https://python-poetry.org/docs/#installation).

## Steps

1. **Install Python using Pyenv**:
   - Check the required Python version for this project in `.python-version` or `pyproject.toml`.
   - Install the required Python version: `pyenv local <python-version>`
2. **Setup Poetry**:
   - Initialize the Poetry environment: `poetry env use python`
   - Install project dependencies: `poetry install`

This setup ensures that all developers work with the same Python version and dependencies, minimizing "works on my machine" issues.