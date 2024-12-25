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
   - Strong type checking for metadata handling

2. Path Generation
   - Configurable path patterns using format strings
   - Sanitization of file and directory names
   - Support for multi-disc albums
   - Type-safe path component handling

3. Database Management
   - SQLite-based state tracking
   - Transaction support for safe operations
   - Artist ID caching for consistent naming
   - Processing state tracking (before/after)
   - Type-checked DAO implementations
   - Database migration support for schema versioning

4. Album Management
   - Grouping tracks by album
   - Track position validation and continuity checking
   - Multi-disc album support
   - Year determination from metadata
   - Robust error handling

5. Filtering System
   - Hierarchical filtering based on metadata
   - Support for album artist and album
   - Customizable organization rules
   - Type-safe filter implementations

Project Structure
---------------

.. code-block:: text

    omym/
    ├── __main__.py          # Package entry point
    ├── main.py              # Main application logic
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
    │   ├── mutagen_types.py     # Type definitions for mutagen
    │   ├── langid_types.pyi     # Type definitions for langid
    │   └── sanitizer.py         # File/path name sanitization
    │
    ├── db/                  # Database management
    │   ├── migrations/          # Database migration scripts
    │   ├── db_manager.py        # Database connection handling
    │   ├── schema.sql           # Database schema
    │   ├── dao_albums.py        # Album data access
    │   ├── dao_artist_cache.py  # Artist cache data access
    │   ├── dao_filter.py        # Filter data access
    │   ├── dao_path_components.py # Path component data access
    │   ├── dao_processing_before.py # Pre-processing state
    │   └── dao_processing_after.py  # Post-processing state
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
    └── tests/               # Test suite
        ├── test_album_manager.py
        ├── test_cli.py
        ├── test_db.py
        ├── test_filtering.py
        ├── test_main.py
        ├── test_metadata_extractor.py
        ├── test_path_generator.py
        ├── test_processor.py
        └── test_renaming_logic.py

Dependencies
-----------

Core Dependencies:
- Python 3.8+
- mutagen: Audio metadata handling
- rich: Terminal UI components
- langid: Language detection
- sqlite3: Database management

Development Dependencies:
- uv: Package management and virtual environment
- pytest: Testing framework
- pylance: Type checking (strict mode)
- ruff: Code style and linting

Environment Variables
------------------

The following environment variables can be used to configure OMYM:

.. code-block:: text

    OMYM_OUTPUT_DIR         # Base output directory for organized files
    OMYM_FILE_FORMAT        # Default file naming format
    OMYM_LOG_LEVEL         # Logging level (DEBUG, INFO, WARNING, ERROR)
    OMYM_DB_PATH           # Custom SQLite database path
    OMYM_CACHE_DIR         # Directory for caching metadata

Type Checking
-----------

OMYM uses strict type checking with Pylance:
- All functions and methods have type hints
- Custom type definitions for external libraries (mutagen, langid)
- Type-safe database operations
- Comprehensive test coverage for type safety

Testing Strategy
--------------

The project uses pytest for testing:
- Unit tests for all core components
- Integration tests for database operations
- Mock objects for external dependencies
- Type checking in test code
- 90%+ test coverage requirement

License
-------

This project is licensed under the MIT License. See the LICENSE file for details. 