Quickstart Guide
==============

This guide will help you get started with OMYM quickly.

Installation
-----------

1. Install using pip:

   .. code-block:: bash

       pip install omym

2. Verify installation:

   .. code-block:: bash

       omym --version

Basic Usage
---------

Preview Mode
~~~~~~~~~~

Before organizing files, use preview mode to see what changes will be made:

.. code-block:: bash

    omym preview /path/to/music

This will show you:
- Which files will be moved
- Their new locations
- Any potential issues

Organize Files
~~~~~~~~~~~~

When you're happy with the preview, organize your files:

.. code-block:: bash

    omym organize /path/to/music

The command will:
1. Extract metadata from your music files
2. Create appropriate directories
3. Move files to their new locations
4. Update the database

Common Options
------------

Path Format
~~~~~~~~~~

Customize the directory structure:

.. code-block:: bash

    omym organize --format "{artist}/{year}_{album}" /path/to/music

File Name Format
~~~~~~~~~~~~~

Customize file names:

.. code-block:: bash

    omym organize --name-format "{track:02d}_{title}" /path/to/music

Dry Run
~~~~~~

Test without making changes:

.. code-block:: bash

    omym organize --dry-run /path/to/music

Next Steps
---------

- Read :doc:`configuration` for detailed configuration options
- Check :doc:`usage` for advanced usage examples
- See :doc:`troubleshooting` if you encounter issues 