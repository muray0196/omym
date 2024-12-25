Configuration Guide
=================

This guide covers the configuration options available in OMYM.

Command Line Options
-----------------

Format Options
~~~~~~~~~~~~

Directory Structure:

.. code-block:: bash

    --format "{artist}/{year}_{album}"

File Names:

.. code-block:: bash

    --name-format "{track:02d}_{title}"

Processing Options
~~~~~~~~~~~~~~~

Dry Run:

.. code-block:: bash

    --dry-run

Force Mode:

.. code-block:: bash

    --force

Output Format:

.. code-block:: bash

    --json

Configuration File
---------------

Location
~~~~~~~

The configuration file is located at:

- Unix: ``~/.config/omym/config.json``
- Windows: ``%USERPROFILE%\.config\omym\config.json``

Format
~~~~~

.. code-block:: json

    {
        "base_path": "/path/to/music/library",
        "log_file": "/path/to/omym.log",
        "config_file": "/path/to/config.json"
    }

Configuration Options
------------------

Base Path
~~~~~~~~

The ``base_path`` setting specifies the root directory of your music library. This is where OMYM will look for music files to organize.

Example:

.. code-block:: json

    {
        "base_path": "/home/user/Music"
    }

Logging
~~~~~~

The ``log_file`` setting specifies where OMYM should write its log output.

Example:

.. code-block:: json

    {
        "log_file": "/home/user/.local/share/omym/omym.log"
    }

Format Strings
------------

Directory Format
~~~~~~~~~~~~~

Available fields:

- ``{artist}``: Artist name (falls back to track artist if missing)
- ``{album}``: Album name (defaults to "Unknown-Album")
- ``{year}``: Release year (uses latest year from album)
- ``{disc}``: Disc number (for multi-disc albums)

Special formatting:

.. code-block:: text

    {year:04d}  # Zero-padded year
    {disc:02d}  # Zero-padded disc number

File Name Format
~~~~~~~~~~~~~

Available fields:

- ``{track}``: Track number
- ``{title}``: Track title
- ``{artist}``: Track artist
- ``{album}``: Album name
- ``{year}``: Release year

Special formatting:

.. code-block:: text

    {track:02d}  # Zero-padded track number
    {title:.30}  # Title truncated to 30 characters 