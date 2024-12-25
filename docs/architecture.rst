Architecture
============

This document describes the high-level architecture of OMYM.

System Components
---------------

.. image:: _static/architecture.png
   :alt: OMYM Architecture Diagram
   :align: center

The system is composed of several key components that work together:

Command Line Interface (CLI)
~~~~~~~~~~~~~~~~~~~~~~~~~~

The CLI layer handles user interaction and command processing:

- Command parsing and validation
- Progress reporting
- Interactive confirmations
- Error reporting

Core Processing
~~~~~~~~~~~~~

The core processing components handle the main business logic:

1. Metadata Extraction
   - File format detection (MP3, FLAC, M4A, DSF)
   - Metadata parsing with mutagen
   - Data normalization and validation
   - Missing metadata handling

2. Path Generation
   - Pattern parsing and validation
   - Artist ID generation and caching
   - Directory structure generation
   - File name generation
   - Collision detection and resolution

3. Album Management
   - Track grouping by album
   - Track position validation
   - Track continuity checking
   - Multi-disc album handling
   - Year determination from metadata

Database Layer
~~~~~~~~~~~~

The database layer manages persistent state:

1. Core Tables
   - processing_before: Original file state
   - processing_after: Processed file state
   - albums: Album information
   - track_positions: Track numbering
   - artist_cache: Cached artist IDs

2. Management
   - SQLite connection handling
   - Transaction management
   - Migration system
   - Data access objects (DAOs)

3. Caching
   - Artist ID caching
   - Processing state caching
   - Album information caching

Processing Flow
-------------

1. Input Processing
   - File/directory path validation
   - Command option parsing
   - Configuration loading
   - Database initialization

2. Metadata Analysis
   - File format detection
   - Metadata extraction
   - Data validation
   - Artist ID generation

3. Organization
   - Album grouping
   - Track position validation
   - Directory path generation
   - File name generation
   - Collision detection

4. Execution
   - Preview generation
   - Database state tracking
   - File operations
   - Error handling

Error Handling
------------

The system implements a robust error handling strategy:

1. Validation Errors
   - Path validation
   - Metadata requirements
   - Format compatibility
   - Track position validation

2. Processing Errors
   - Metadata extraction failures
   - Path generation issues
   - Database errors
   - File operation errors

3. System Errors
   - File system errors
   - Permission issues
   - Resource constraints
   - Database connection issues

Data Flow
--------

.. code-block:: text

    Input Files
        │
        ▼
    Metadata Extraction
        │
        ▼
    Artist ID Generation
        │
        ▼
    Album Grouping
        │
        ▼
    Track Position Validation
        │
        ▼
    Path Generation
        │
        ▼
    Database State Tracking
        │
        ▼
    File Operations

Configuration
-----------

The system is configurable through:

1. Command Line Options
   - Path format patterns
   - Processing modes
   - Output control
   - Dry run mode

2. Environment Variables
   - Database settings
   - Logging configuration
   - Default formats

3. Configuration File
   - Path settings
   - Japanese text handling
   - Error handling
   - Cache settings

Extension Points
-------------

The system can be extended through:

1. Metadata Extractors
   - Support for additional formats
   - Custom metadata fields
   - New metadata sources

2. Path Generators
   - Custom naming patterns
   - Special handling rules
   - New format fields

3. Filters
   - New hierarchy types
   - Custom filter conditions
   - Metadata processors 