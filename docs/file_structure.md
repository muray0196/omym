# OMYM File Structure Documentation

## Overview
This document details the essential organization of OMYM's files and directories.

## Directory Structure

```
omym/                      # Project root
├── README.md
├── config/
│   └── config.toml
├── data/
│   └── omym.db
├── omym/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── metadata/
│   │   │   ├── __init__.py
│   │   │   ├── metadata.py
│   │   │   ├── metadata_extractor.py
│   │   │   ├── processor.py
│   │   │   └── types/
│   │   │       ├── __init__.py
│   │   │       ├── langid_types.pyi
│   │   │       └── mutagen_types.py
│   │   ├── operations/
│   │   │   ├── __init__.py
│   │   │   ├── organize.py
│   │   │   └── preview.py
│   │   ├── organization/
│   │   │   ├── __init__.py
│   │   │   ├── album_manager.py
│   │   │   ├── filtering.py
│   │   │   └── music_grouper.py
│   │   └── path/
│   │       ├── __init__.py
│   │       ├── path_components.py
│   │       ├── path_generator.py
│   │       ├── renaming_logic.py
│   │       └── sanitizer.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── db_manager.py
│   │   ├── cache/
│   │   │   ├── __init__.py
│   │   │   └── dao_artist_cache.py
│   │   ├── daos/
│   │   │   ├── __init__.py
│   │   │   ├── dao_albums.py
│   │   │   ├── dao_filter.py
│   │   │   ├── dao_path_components.py
│   │   │   ├── dao_processing_after.py
│   │   │   └── dao_processing_before.py
│   │   └── migrations/
│   │       ├── __init__.py
│   │       ├── schema.sql
│   │       └── versions/
│   │           └── 001_initial.sql
│   ├── ui/
│   │   ├── __init__.py
│   │   └── cli.py
│   └── utils/
│       ├── __init__.py
│       └── logger.py
└── pyproject.toml
```

## File Naming Conventions

### 1. Python Files
- All lowercase with underscores for word separation
- Module files use descriptive nouns or noun phrases (e.g., `album_manager.py`, `path_generator.py`)
- Special files use double underscores (e.g., `__init__.py`, `__main__.py`)
- Test files:
  - Prefixed with `test_`
  - Mirror the name of the module they test (e.g., `test_album_manager.py`)
- Type hints:
  - Use `.pyi` extension for stub files
  - Append `_types` for type definition modules (e.g., `mutagen_types.py`)

## Directory Purposes

### 1. Root Level Directories
- `config/` - Application configuration files (TOML format)
  - Contains `config.toml` for application settings
  - Supports environment-specific configurations
- `data/` - Database storage
  - Contains `omym.db` SQLite database file
  - Stores processed music metadata and cache
  - Maintains processing state and artist information
- `docs/` - Project documentation in Markdown
  - Each document focuses on a specific aspect of the project
  - Follows Google Style Markdown conventions
  - Includes diagrams and structured documentation
- `omym/` - Main Python package

### 2. Main Package (`omym/`)
- Entry point (`__main__.py`)
- Configuration handling (`config.py`)
- Main application logic (`main.py`)
- Modular subpackages for specific functionality

### 3. Core Module (`core/`)
- Metadata handling (`metadata/`)
  - Music metadata extraction and processing
  - Type definitions for external libraries
  - Metadata models and processors
- Operations (`operations/`)
  - High-level operations like organize and preview
  - Command execution logic
- Organization (`organization/`)
  - Album and artist management
  - File filtering and grouping
  - Music organization logic
- Path handling (`path/`)
  - Path generation and naming
  - File name sanitization
  - Path components management

### 4. Database Module (`db/`)
- Data Access Objects (`daos/`)
  - Album and artist management
  - Processing state (before/after)
  - Path components and filters
- Cache management (`cache/`)
  - Artist ID caching
  - Performance optimization
- Database management and migrations
  - Version-controlled schema changes in `migrations/versions/`
  - Each migration is timestamped and reversible
  - Automatic migration application on startup
- SQL schema definition
  - Base schema in `migrations/schema.sql`
  - Defines tables, indices, and constraints
  - Documents table relationships and purposes

### 5. UI Module (`ui/`)
- Command-line interface implementation (`cli.py`)
- User input processing
- Output formatting

### 6. Utils Module (`utils/`)
- Logging configuration and management (`logger.py`)
- General utility functions and helpers