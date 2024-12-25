Architecture
============

This document describes the high-level architecture of OMYM.

System Components
---------------

The system is composed of several key components that work together:

Command Line Interface (CLI)
~~~~~~~~~~~~~~~~~~~~~~~~~~

The CLI layer handles user interaction and command processing:

- Command parsing and validation
- Progress reporting with rich library
- Interactive confirmations for file operations
- Detailed error reporting with context
- Dry-run mode for safe preview

Core Processing
~~~~~~~~~~~~~

The core processing components handle the main business logic:

1. Metadata Extraction
   - File format detection (MP3, FLAC, M4A, DSF)
   - Type-safe metadata parsing with mutagen
   - Comprehensive data validation
   - Robust error handling for missing metadata
   - Custom type definitions for external libraries
   - Modular metadata handling with dedicated package structure

2. Path Generation
   - Type-safe pattern parsing and validation
   - Directory structure generation
   - File name generation with sanitization
   - Collision detection and resolution
   - Path component validation
   - Robust path and filename sanitization

3. Album Management
   - Type-safe track grouping by album
   - Track position validation
   - Track continuity checking
   - Multi-disc album handling
   - Intelligent year determination

Database Layer
~~~~~~~~~~~~

The database layer manages persistent state:

1. Core Tables
   - processing_before: Original file state
   - processing_after: Processed file state
   - albums: Album information
   - track_positions: Track numbering
   - artist_cache: Cached artist IDs
   - filter_hierarchies: Organization rules
   - filter_values: Applied filters

2. Management
   - Type-safe SQLite connection handling
   - Transaction management for data integrity
   - Data access objects (DAOs) with type checking
   - Error handling with rollback support
   - Database schema migrations for versioning

3. Caching
   - Artist ID caching for consistency
   - Processing state tracking
   - Album information caching
   - Filter hierarchy caching

Processing Flow
-------------

1. Input Processing
   - File/directory path validation
   - Command option parsing with type checking
   - Configuration loading and validation
   - Database initialization and migration
   - Path and filename sanitization

2. Metadata Analysis
   - Type-safe file format detection
   - Metadata extraction with error handling
   - Data validation and normalization
   - Artist ID generation and caching
   - Modular metadata processing

3. Organization
   - Type-safe album grouping
   - Track position validation
   - Directory path generation
   - File name generation with collision handling
   - Filter application
   - Path sanitization

4. Execution
   - Preview generation in dry-run mode
   - Database state tracking
   - Atomic file operations
   - Comprehensive error handling
   - Progress reporting

Error Handling
------------

The system implements a robust error handling strategy:

1. Validation Errors
   - Path validation with type checking
   - Metadata requirements validation
   - Format compatibility checking
   - Track position validation
   - Filter hierarchy validation
   - Path sanitization validation

2. Processing Errors
   - Type-safe metadata extraction
   - Path generation error handling
   - Database operation errors
   - File operation failures
   - Cache management errors
   - Sanitization errors

3. System Errors
   - File system error handling
   - Permission issue detection
   - Resource constraint handling
   - Database connection error recovery
   - Type checking errors
   - Migration errors

Data Flow
--------

.. code-block:: text

    Input Files
        │
        ▼
    Type Validation & Format Detection
        │
        ▼
    Metadata Extraction
        │
        ▼
    Data Validation & Normalization
        │
        ▼
    Artist ID Generation & Caching
        │
        ▼
    Album Grouping & Validation
        │
        ▼
    Track Position Validation
        │
        ▼
    Filter Application
        │
        ▼
    Path Generation & Sanitization
        │
        ▼
    Database State Tracking
        │
        ▼
    File Operations (or Preview)

Configuration
-----------

The system is configurable through:

1. Command Line Options
   - Path format patterns
   - Processing modes (organize, preview)
   - Output control (quiet, verbose)
   - Dry run mode
   - Format selection

2. Environment Variables
   - OMYM_OUTPUT_DIR: Output directory
   - OMYM_FILE_FORMAT: File naming format
   - OMYM_LOG_LEVEL: Logging configuration
   - OMYM_DB_PATH: Database location
   - OMYM_CACHE_DIR: Cache directory

3. Type Safety
   - Runtime type checking
   - Configuration validation
   - Format string validation
   - Path pattern validation
   - Sanitization rules validation

Extension Points
-------------

The system can be extended through:

1. Metadata Extractors
   - Support for additional audio formats
   - Custom metadata field extraction
   - New metadata sources
   - Type-safe extraction interfaces
   - Metadata package extensions

2. Path Generators
   - Custom naming patterns
   - Special handling rules
   - New format fields
   - Type-safe path generation
   - Custom sanitization rules

3. Filters
   - New hierarchy types
   - Custom filter conditions
   - Type-safe filter implementations
   - Metadata processors 