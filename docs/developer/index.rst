Developer Guide
==============

This guide is intended for developers who want to contribute to OMYM or understand its internals.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   setup
   contributing
   testing
   code_style
   architecture/index

Development Environment
--------------------

OMYM development requires:

- Python 3.13+
- uv for dependency management
- pytest for testing
- ruff for code formatting and linting

Setting Up
---------

1. Clone the repository:

   .. code-block:: bash

       git clone https://github.com/yourusername/omym.git
       cd omym

2. Create a virtual environment and install dependencies:

   .. code-block:: bash

       uv venv
       source .venv/bin/activate  # On Unix
       # or
       .venv\Scripts\activate  # On Windows
       uv pip install -e ".[dev]"

3. Run tests to verify setup:

   .. code-block:: bash

       uv run pytest

Development Workflow
-----------------

1. Create a new branch for your feature/fix:

   .. code-block:: bash

       git checkout -b feature/your-feature-name

2. Make your changes, following our coding standards

3. Run tests and linting:

   .. code-block:: bash

       uv run pytest
       ruff check .
       ruff format .

4. Commit your changes:

   .. code-block:: bash

       git add .
       git commit -m "Description of changes"

5. Push and create a pull request

Code Organization
--------------

The project follows a modular structure:

- ``core/``: Core business logic
- ``db/``: Database management
- ``commands/``: CLI commands
- ``ui/``: User interface components
- ``tests/``: Test suite

Contributing
----------

See :doc:`contributing` for detailed contribution guidelines.

Testing
------

See :doc:`testing` for information about our testing approach.

Code Style
--------

See :doc:`code_style` for our coding standards and style guide. 