Installation Guide
=================

This guide covers the installation process for OMYM.

Requirements
----------

- Python 3.8 or later
- pip (Python package installer)
- 50MB free disk space

Installation Steps
---------------

Using pip
~~~~~~~~

The recommended way to install OMYM is using pip:

.. code-block:: bash

    pip install omym

This will install OMYM and all its dependencies.

Verifying Installation
-------------------

After installation, verify that OMYM is working:

.. code-block:: bash

    omym --version

You should see the version number of OMYM displayed.

Test the installation with:

.. code-block:: bash

    omym --help

This should display the help message with available commands.

Environment Setup
--------------

While not required, you can set up environment variables for convenience:

1. Output Directory
   
   .. code-block:: bash

       export OMYM_OUTPUT_DIR=~/OrganizedMusic

2. Default Format
   
   .. code-block:: bash

       export OMYM_FILE_FORMAT="{artist}/{album}/{track:02d} {title}"

3. Log Level
   
   .. code-block:: bash

       export OMYM_LOG_LEVEL=INFO

Add these to your shell's startup file (e.g., .bashrc, .zshrc) to make them permanent.

Supported Platforms
----------------

OMYM is tested on:
- Linux (Ubuntu, Fedora, Debian)
- macOS (10.15+)
- Windows 10/11

Troubleshooting
-------------

Common Issues
~~~~~~~~~~~

1. Python Version Error
   
   If you see an error about Python version:
   - Check your Python version: `python --version`
   - Install Python 3.8 or later if needed

2. Permission Error
   
   If you get permission errors:
   - Use `pip install --user omym`
   - Or use a virtual environment

3. Missing Dependencies
   
   If dependencies fail to install:
   - Update pip: `pip install --upgrade pip`
   - Try installing dependencies manually

Getting Help
~~~~~~~~~~

If you encounter issues:
1. Check the error message carefully
2. Look for similar issues on GitHub
3. File a new issue if needed

Uninstallation
------------

To remove OMYM:

.. code-block:: bash

    pip uninstall omym

This will remove OMYM while keeping your music files and configurations intact. 