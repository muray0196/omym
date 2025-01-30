# OMYM File Structure Documentation

## Overview
This document details the essential organization of OMYM's files and directories, providing a clear understanding of the project's structure and component purposes.

## Directory Structure

```
omym/
├── README.md
├── docs/
│   ├── file_structure.md
│   ├── project_requirements.md
│   ├── tech_stack.md
│   ├── tool_flow.md
│   ├── tool_logic_structure.md
│   └── ui_guidelines.md
├── omym/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── metadata/
│   │   │   ├── __init__.py
│   │   │   ├── music_file_processor.py
│   │   │   ├── track_metadata.py
│   │   │   └── track_metadata_extractor.py
│   │   ├── organization/
│   │   │   ├── __init__.py
│   │   │   ├── album_manager.py
│   │   │   ├── filter_engine.py
│   │   │   └── group_manager.py
│   │   └── path/
│   │       ├── __init__.py
│   │       ├── music_file_renamer.py
│   │       ├── path_elements.py
│   │       ├── path_generator.py
│   │       └── sanitizer.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── cache/
│   │   │   ├── __init__.py
│   │   │   └── artist_cache_dao.py
│   │   ├── daos/
│   │   │   ├── __init__.py
│   │   │   ├── albums_dao.py
│   │   │   ├── filter_dao.py
│   │   │   ├── path_elements_dao.py
│   │   │   ├── processing_after_dao.py
│   │   │   └── processing_before_dao.py
│   │   ├── db_manager.py
│   │   └── migrations/
│   │       ├── __init__.py
│   │       ├── schema.sql
│   │       └── versions/
│   │           └── 001_initial.sql
│   ├── main.py
│   ├── types/
│   │   ├── __init__.py
│   │   ├── langid_types.pyi
│   │   └── mutagen_types.py
│   ├── ui/
│   │   ├── __init__.py
│   │   └── cli.py
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── pyproject.toml
└── tests/
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
- `docs/` - Project documentation in Markdown
  - Each document focuses on a specific aspect of the project
  - Follows Google Style Markdown conventions
  - Includes diagrams and structured documentation
- `omym/` - Main Python package
- `tests/` - Test suite directory mirroring the main package structure

### 2. Main Package (`omym/`)
- Entry point (`__main__.py`)
- Configuration handling (`config.py`)
- Main application logic (`main.py`)
- Modular subpackages for specific functionality

### 3. Core Module (`core/`)
- Metadata handling (`metadata/`)
  - Music metadata extraction and processing
  - Metadata models and processors
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
  - Processing state tracking
  - Path components and filters
- Cache management (`cache/`)
  - Artist ID caching
  - Performance optimization
- Database management (`migrations/`)
  - Version-controlled schema changes
  - Automatic migration application
  - Base schema and table definitions

### 5. Types Module (`types/`)
- Purpose: Resolves type-related issues and enhances type safety
- Contains type definitions and stubs for external libraries
- Provides type hints for project-specific components
- Helps maintain strict type checking across the codebase
- Includes:
  - Stub files (`.pyi`) for external library type definitions
  - Custom type definitions for project-specific types
  - Type aliases and protocols for complex types

### 6. UI Module (`ui/`)
- Command-line interface implementation (`cli.py`)
- User input processing and validation
- Output formatting and display

### 7. Utils Module (`utils/`)
- Logging configuration and management (`logger.py`)
- General utility functions and helpers
- Common functionality used across modules