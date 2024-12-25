Project Overview
===============

What is OMYM?
------------

OMYM (Organize My Music) is a Python-based command-line tool designed to help users organize their music libraries efficiently. It analyzes music file metadata and organizes files into a consistent directory structure based on configurable patterns.

Core Components
-------------

The project is organized into several core components:

1. Metadata Extraction
   - Supports multiple audio formats (MP3, FLAC, M4A, DSF)
   - Extracts comprehensive metadata including artist, album, track numbers, etc.
   - Handles missing or incomplete metadata gracefully

2. Path Generation
   - Configurable path patterns using format strings
   - Sanitization of file and directory names
   - Handling of special characters and different languages
   - Support for multi-disc albums

3. Database Management
   - SQLite-based state tracking
   - Transaction support for safe operations
   - Artist ID caching for consistent naming
   - Processing state tracking (before/after)

4. Album Management
   - Grouping tracks by album
   - Track position validation and continuity checking
   - Multi-disc album support
   - Year determination from metadata

5. Filtering System
   - Hierarchical filtering based on metadata
   - Support for album artist, album, and genre
   - Customizable organization rules

Project Structure
---------------

.. code-block:: text

    omym/
    ├── __main__.py          # Package entry point
    ├── main.py              # Main application logic
    ├── cli.py               # Command-line interface
    ├── config.py            # Configuration handling
    │
    ├── core/                # Core functionality
    │   ├── metadata.py          # Metadata data structures
    │   ├── metadata_extractor.py # Audio metadata extraction
    │   ├── album_manager.py     # Album organization logic
    │   ├── path_generator.py    # Path generation logic
    │   ├── path_components.py   # Path component handling
    │   ├── renaming_logic.py    # File renaming logic
    │   ├── processor.py         # File processing logic
    │   ├── music_grouper.py     # Music file grouping
    │   ├── filtering.py         # Filtering system
    │   └── sanitizer.py         # Name sanitization
    │
    ├── db/                  # Database management
    │   ├── db_manager.py        # Database connection handling
    │   ├── schema.sql           # Database schema
    │   ├── dao_albums.py        # Album data access
    │   ├── dao_artist_cache.py  # Artist cache data access
    │   ├── dao_filter.py        # Filter data access
    │   ├── dao_path_components.py # Path component data access
    │   ├── dao_processing_before.py # Pre-processing state
    │   ├── dao_processing_after.py  # Post-processing state
    │   └── migrations/          # Database migrations
    │       └── 001_initial.sql  # Initial schema
    │
    ├── commands/            # CLI commands
    │   ├── organize.py          # Organize command
    │   └── preview.py           # Preview command
    │
    ├── ui/                  # User interface
    │   └── cli.py              # CLI implementation
    │
    ├── utils/               # Utilities
    │   └── logger.py           # Logging configuration
    │
    ├── tests/               # Test suite
    │   ├── test_renaming_logic.py
    │   ├── test_processor.py
    │   ├── test_cli.py
    │   └── test_path_generator.py
    │
    └── docs/                # Documentation
        ├── index.rst
        ├── overview.rst
        ├── architecture.rst
        ├── user/
        │   ├── index.rst
        │   ├── quickstart.rst
        │   ├── installation.rst
        │   ├── usage.rst
        │   ├── configuration.rst
        │   └── troubleshooting.rst
        └── developer/
            ├── index.rst
            ├── contributing.rst
            ├── testing.rst
            └── code_style.rst

Dependencies
-----------

- Python 3.13+
- mutagen: Audio metadata handling
- rich: Terminal UI components
- pykakasi: Japanese text processing
- langid: Language detection
- unidecode: Unicode character handling
- sqlite3: Database management

License
-------

This project is licensed under the MIT License. See the LICENSE file for details. 