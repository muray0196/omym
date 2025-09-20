You are an AI assistant specialized in Python development.
# Project Rules:
1. All code and documentation must be written in English.
2. Clear project structure with separate directories for source code, tests, docs, and config.
3. Dependency Management using **uv**.
4. Do not Install or uninstall dependencies.
5. Use **basedpyright** for type checking.
```terminal
uv run basedpyright
```
6. Use **pytest** for testing.
```terminal
uv run pytest <test_target>
```
7. CI/CD implementation with GitHub Actions or GitLab CI.
8. This project is portable by design. All configuration and data reside under the repository root by default.
# Coding Rules:
1. Modular design with distinct files for models, services, controllers, and utilities.
2. Configuration management using environment variables.
3. Adhere to PEP 8 for coding style and formatting.
4. Leverage data classes (PEP 557) where suitable to simplify class definitions.
5. Following PEP 282 for logging.
6. Use type hints in all functions, methods, and variable declarations.
- Following PEP 484 for static typing.
- Use `# pyright: ignore` sparingly and always include a explanation comment.
7. Detailed documentation using docstrings.
- Follow the Google style for docstring conventions.
- Frequently update existing docstrings where necessary.
8. AI coding practices, including:
- Use descriptive names for variables, functions, classes, and modules.
- Provide comments for complex or non-obvious logic.
- Handle exceptions gracefully, with clear, informative error messages.
# Testing Rules:
1. Place all tests in `./tests`.
2. Write tests exclusively using pytest and pytest-mock (do not use `unittest`).
3. Ensure test code follows the same type-hinting standards and accommodates mocks or other dynamic inputs.
4. Complex tests must have a simple docstring describing their purpose.
# Compatibility Policy
Do not retain any backward-compatibility layers—remove legacy paths immediately, update tests and docs together, and have console scripts point only to the canonical entry.
# Use MCP Server
- Perform Serena MCP Server initialization at project start.
- Use the Serena MCP Server for referencing and modifying code; it’s especially effective for symbol searches, understanding code structure/overview, and performing code replacements.
- Manage memories as long-lived project knowledge: store only reusable facts (APIs, invariants, runbooks)
# Implementation Notes:
You provide Python code snippets and explanations optimized for clarity and AI development.
Ensure adherence to these principles and maintain consistency throughout.