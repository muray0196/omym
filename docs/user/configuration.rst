Configuration Guide
=================

This guide explains how to configure OMYM to suit your needs.

Environment Variables
------------------

Basic Settings
~~~~~~~~~~~

OMYM_OUTPUT_DIR
    Base directory for organized files
    Default: Current directory
    Example: ``export OMYM_OUTPUT_DIR=~/OrganizedMusic``

OMYM_FILE_FORMAT
    Default file naming format
    Default: ``{artist}/{album}/{track:02d} {title}``
    Example: ``export OMYM_FILE_FORMAT="{artist}/{album} ({year})/{track:02d} {title}"``

OMYM_LOG_LEVEL
    Logging verbosity
    Values: DEBUG, INFO, WARNING, ERROR
    Default: INFO
    Example: ``export OMYM_LOG_LEVEL=DEBUG``

Advanced Settings
~~~~~~~~~~~~~~

OMYM_DB_PATH
    Custom database location
    Default: ~/.local/share/omym/omym.db
    Example: ``export OMYM_DB_PATH=~/Music/.omym/db.sqlite``

OMYM_CACHE_DIR
    Directory for caching metadata
    Default: ~/.cache/omym
    Example: ``export OMYM_CACHE_DIR=~/Music/.omym/cache``

Format Patterns
-------------

Directory Structure
~~~~~~~~~~~~~~~~

The directory structure can be customized using format strings:

Basic Pattern:
    ``{artist}/{album}``
    Creates: Artist/Album/

With Year:
    ``{artist}/{album} ({year})``
    Creates: Artist/Album (2023)/

Multi-disc Albums:
    ``{artist}/{album}/Disc {disc}``
    Creates: Artist/Album/Disc 1/

File Names
~~~~~~~~

File names can be customized using format strings:

Basic Pattern:
    ``{track:02d} {title}``
    Creates: 01 Song Title.mp3

With Track Artist:
    ``{track:02d} {artist} - {title}``
    Creates: 01 Artist - Song Title.mp3

Available Variables
---------------

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
    Album artist (for compilations)
    Example: "Various Artists"

{disc}
    Disc number
    Example: "1" or "01" with :02d

{year}
    Release year
    Example: "1969"

{genre}
    Genre
    Example: "Rock"

Format Modifiers
-------------

Number Formatting
~~~~~~~~~~~~~~

:02d
    Zero-pad numbers to 2 digits
    Example: "{track:02d}" → "01"

:03d
    Zero-pad numbers to 3 digits
    Example: "{track:03d}" → "001"

Text Formatting
~~~~~~~~~~~~

:s
    Convert to safe filename
    Example: "{title:s}" → "Song_Title"

:lower
    Convert to lowercase
    Example: "{artist:lower}" → "artist name"

:upper
    Convert to uppercase
    Example: "{artist:upper}" → "ARTIST NAME"

Examples
-------

Complete Examples
~~~~~~~~~~~~~~

1. Basic Organization:

   .. code-block:: bash

       export OMYM_OUTPUT_DIR=~/Music/Organized
       export OMYM_FILE_FORMAT="{artist}/{album}/{track:02d} {title}"

2. Year-based Organization:

   .. code-block:: bash

       export OMYM_FILE_FORMAT="{year}/{artist}/{album}/{track:02d} {title}"

3. Genre-based Organization:

   .. code-block:: bash

       export OMYM_FILE_FORMAT="{genre}/{artist}/{album}/{track:02d} {title}"

4. Multi-disc Albums:

   .. code-block:: bash

       export OMYM_FILE_FORMAT="{artist}/{album}/Disc {disc:02d}/{track:02d} {title}"

Best Practices
------------

1. Use Consistent Patterns
   - Choose a format and stick to it
   - Consider file sorting
   - Use clear separators

2. Handle Special Cases
   - Multi-disc albums
   - Compilation albums
   - Various artists

3. Safe Characters
   - Use :s modifier for paths
   - Avoid special characters
   - Consider filesystem limits

4. Logging
   - Use DEBUG for troubleshooting
   - Use INFO for normal operation
   - Check logs for issues

Troubleshooting
-------------

Common Issues
~~~~~~~~~~

1. Missing Variables
   - Check format string syntax
   - Verify metadata availability
   - Use preview mode to test

2. Path Length Issues
   - Simplify format patterns
   - Use shorter variables
   - Consider filesystem limits

3. Permission Issues
   - Check directory permissions
   - Verify file access rights
   - Use appropriate paths 