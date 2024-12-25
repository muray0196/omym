Usage Guide
===========

This guide covers the detailed usage of OMYM.

Basic Commands
------------

Preview
~~~~~~~

Preview changes without modifying files:

.. code-block:: bash

    omym preview /path/to/music

Options:
- ``--format``: Directory structure format
- ``--name-format``: File name format
- ``--json``: Output in JSON format

Organize
~~~~~~~

Organize files based on metadata:

.. code-block:: bash

    omym organize /path/to/music

Options:
- ``--dry-run``: Show changes without executing
- ``--format``: Directory structure format
- ``--name-format``: File name format
- ``--force``: Skip confirmations

Path Formats
----------

Directory Format
~~~~~~~~~~~~~

The directory structure can be customized using format strings:

.. code-block:: bash

    omym organize --format "{artist}/{year}_{album}" /path/to/music

Available fields:
- ``{artist}``: Artist name
- ``{album}``: Album name
- ``{year}``: Release year
- ``{genre}``: Genre
- ``{disc}``: Disc number

File Name Format
~~~~~~~~~~~~~

File names can be customized using format strings:

.. code-block:: bash

    omym organize --name-format "{track:02d}_{title}" /path/to/music

Available fields:
- ``{track}``: Track number
- ``{title}``: Track title
- ``{artist}``: Track artist
- ``{album}``: Album name
- ``{year}``: Release year

Advanced Usage
------------

Filtering
~~~~~~~~

Filter files based on metadata:

.. code-block:: bash

    omym organize --filter "year>2000" /path/to/music

Filter operators:
- ``>``, ``<``, ``=``: Comparison
- ``&``, ``|``: Logical AND, OR
- ``()``: Grouping

Multi-disc Albums
~~~~~~~~~~~~~~

Handle multi-disc albums:

.. code-block:: bash

    omym organize --format "{artist}/{year}_{album}/Disc {disc}" /path/to/music

Japanese Support
~~~~~~~~~~~~~

Handle Japanese artist names and titles:

.. code-block:: bash

    omym organize --format "{artist_id}/{year}_{album}" /path/to/music

The ``artist_id`` field generates a romanized ID for Japanese artists.

Database Management
----------------

View Status
~~~~~~~~~

Check processing status:

.. code-block:: bash

    omym status

Reset Database
~~~~~~~~~~~

Clear the database:

.. code-block:: bash

    omym reset

Error Handling
-----------

Missing Metadata
~~~~~~~~~~~~~

When metadata is missing:
1. Warnings are displayed
2. Default values are used
3. Files are marked for review

File Conflicts
~~~~~~~~~~~

When file conflicts occur:
1. Unique suffixes are added
2. Original files are preserved
3. Conflicts are logged

Best Practices
------------

1. Always use preview first
2. Back up important files
3. Use dry-run for testing
4. Check logs for issues
5. Maintain consistent naming 