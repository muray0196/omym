Usage Guide
===========

This guide covers the main features and usage patterns of OMYM.

Basic Commands
------------

Preview Mode
~~~~~~~~~~

Before organizing files, use preview mode to see what changes will be made:

.. code-block:: bash

    omym preview /path/to/music

The preview shows:
- Files to be processed
- New directory structure
- New file names
- Potential issues or warnings

Organization Mode
~~~~~~~~~~~~~~

To actually organize your files:

.. code-block:: bash

    omym organize /path/to/music

This will:
1. Analyze music files
2. Create directory structure
3. Copy files to new locations
4. Report results

Command Options
-------------

Common Options
~~~~~~~~~~~

--format FORMAT
    Specify the output path format
    Example: --format "{artist}/{album}/{track:02d} {title}"

--output DIR
    Set the output directory
    Example: --output ~/OrganizedMusic

--verbose
    Show detailed progress information

--quiet
    Suppress non-essential output

Format Variables
-------------

Basic Variables
~~~~~~~~~~~~

{artist}
    Artist name
    Example: "The Beatles"

{album}
    Album name
    Example: "Abbey Road"

{track}
    Track number
    Example: "1" or "01" with :02d

{title}
    Track title
    Example: "Come Together"

Additional Variables
~~~~~~~~~~~~~~~~

{album_artist}
    Album artist (compilation albums)
    Example: "Various Artists"

{disc}
    Disc number for multi-disc albums
    Example: "1" or "01" with :02d

{year}
    Release year
    Example: "1969"

{genre}
    Genre
    Example: "Rock"

Format Modifiers
~~~~~~~~~~~~~

:02d
    Zero-pad numbers
    Example: "{track:02d}" → "01" instead of "1"

:s
    Convert to safe filename
    Example: "{title:s}" → "Track_Title" instead of "Track/Title"

Examples
-------

Basic Organization
~~~~~~~~~~~~~~~

Organize with default settings:

.. code-block:: bash

    omym organize ~/Music

Custom Format
~~~~~~~~~~

Use a specific naming pattern:

.. code-block:: bash

    omym organize ~/Music --format "{artist}/{album} ({year})/{disc:02d}-{track:02d} {title}"

This creates:
Artist/Album (Year)/01-05 Song.mp3

Multiple Directories
~~~~~~~~~~~~~~~~

Process multiple directories:

.. code-block:: bash

    omym organize ~/Music ~/Downloads/NewMusic

Specific Output
~~~~~~~~~~~~

Set a custom output location:

.. code-block:: bash

    omym organize ~/Music --output ~/OrganizedMusic

Best Practices
------------

1. Always Preview First
   - Use preview mode before organizing
   - Check for potential issues
   - Verify the new structure

2. Backup Important Files
   - Keep backups of important music
   - Use preview mode to verify changes
   - Check results after organizing

3. Use Descriptive Formats
   - Include relevant metadata
   - Use consistent patterns
   - Consider file sorting

4. Handle Special Cases
   - Multi-disc albums
   - Compilation albums
   - Various artists

Common Issues
-----------

Missing Metadata
~~~~~~~~~~~~~

If files have missing metadata:
1. Files will be skipped
2. Warning messages will show
3. Check original files

Name Conflicts
~~~~~~~~~~~

When duplicate names occur:
1. Unique suffixes are added
2. Original files are preserved
3. Warnings are displayed

Special Characters
~~~~~~~~~~~~~~~

For problematic characters:
1. Automatic sanitization
2. Safe filename conversion
3. Consistent handling

Getting Help
----------

Command Help
~~~~~~~~~~

View available commands:

.. code-block:: bash

    omym --help

View command options:

.. code-block:: bash

    omym organize --help

Troubleshooting
~~~~~~~~~~~~

If you encounter issues:
1. Check error messages
2. Use --verbose for details
3. Consult troubleshooting guide
4. Report issues on GitHub 