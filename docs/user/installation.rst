Installation Guide
=================

This guide covers the installation of OMYM and its dependencies.

System Requirements
----------------

- Python 3.13 or higher
- SQLite 3.x
- Sufficient disk space for your music library

Installation Methods
-----------------

Using pip
~~~~~~~~

The recommended way to install OMYM is using pip:

.. code-block:: bash

    pip install omym

Using uv (Recommended)
~~~~~~~~~~~~~~~~~~~

For better dependency management, you can use uv:

.. code-block:: bash

    uv pip install omym

From Source
~~~~~~~~~

To install from source:

1. Clone the repository:

   .. code-block:: bash

       git clone https://github.com/yourusername/omym.git
       cd omym

2. Install using uv:

   .. code-block:: bash

       uv pip install -e .

Development Installation
---------------------

For development purposes, install with additional dependencies:

.. code-block:: bash

    uv pip install -e ".[dev]"

This includes:
- Testing tools (pytest)
- Linting tools (ruff)
- Documentation tools (sphinx)

Verifying Installation
-------------------

1. Check version:

   .. code-block:: bash

       omym --version

2. Run self-test:

   .. code-block:: bash

       omym test

Dependencies
----------

Core Dependencies
~~~~~~~~~~~~~~

- mutagen: Audio metadata handling
- rich: Terminal UI
- pykakasi: Japanese text processing
- langid: Language detection
- unidecode: Unicode character handling

Optional Dependencies
~~~~~~~~~~~~~~~~~

Development tools:
- pytest: Testing framework
- ruff: Code linting and formatting
- sphinx: Documentation generation

Troubleshooting
-------------

Common Issues
~~~~~~~~~~~

1. Python Version
   
   If you see a Python version error:
   - Check your Python version: ``python --version``
   - Ensure you have Python 3.13+

2. SQLite Issues
   
   If you encounter SQLite errors:
   - Check SQLite installation: ``sqlite3 --version``
   - Ensure write permissions in the database directory

3. Dependency Conflicts
   
   If you see dependency conflicts:
   - Try using a virtual environment
   - Use uv for better dependency resolution

Getting Help
----------

If you encounter issues:

1. Check the :doc:`troubleshooting` guide
2. Search existing GitHub issues
3. Create a new issue with:
   - Your system information
   - Installation method used
   - Complete error message
   - Steps to reproduce 