# OMYM Tool Logic Structure

## Overview
This document describes the internal structure of OMYM's logic, detailing how different modules and components work together to organize music libraries.

## Core Components

### 1. Music Processing
- **Processor** (`core/processor.py`)
  - Central processing coordinator
  - File operation management
  - Process state tracking
  - Error handling
  - File hash calculation

- **Metadata Management** (`core/metadata_extractor.py`, `core/metadata.py`)
  - Audio file parsing
  - Tag extraction and validation
  - Format-specific handling (MP3, FLAC, M4A, DSF, AAC, ALAC, Opus)
  - Metadata model definitions

### 2. Music Organization
- **Album Management** (`core/album_manager.py`, `core/music_grouper.py`)
  - Track grouping by album
  - Album metadata consolidation
  - Multi-disc handling
  - Track position management

- **Path Generation** (`core/path_generator.py`, `core/path_components.py`)
  - Directory structure generation
  - File path creation
  - Path conflict resolution
  - Component management

### 3. Text Processing
- **Artist ID Generation** (`core/renaming_logic.py`)
  - Artist name processing
  - Up to 5-character ID generation (no padding)
  - Caching mechanism
  - Language-specific handling

- **Name Sanitization** (`core/sanitizer.py`)
  - Character replacement
  - Platform compatibility
  - Special character handling
  - Path validation

### 4. File Filtering
- **Music File Filtering** (`core/filtering.py`)
  - File type detection (.mp3, .flac, .m4a, .dsf, .aac, .alac, .opus)
  - Filter rule application
  - Hierarchy management
  - Filter persistence

## Operations Layer

### 1. Core Operations
- **Operations** (`core/operations/`)
  - `organize.py`: Music library organization
  - `preview.py`: Change preview functionality
  - Transaction management
  - State tracking

## Data Layer

### 1. Database Management
- **Core Database** (`db/db_manager.py`)
  - Connection management
  - Transaction handling
  - Migration support
  - Schema management

### 2. Data Access Objects
- **Processing DAOs** (`db/`)
  - `dao_processing_before.py`: Initial state
  - `dao_processing_after.py`: Final state
  - `dao_albums.py`: Album management
  - `dao_artist_cache.py`: Artist ID caching
  - `dao_filter.py`: Filter rules
  - `dao_path_components.py`: Path components

### 3. Schema Design (`db/schema.sql`)
- **Tables**
  - Processing state tables
  - Album and track tables
  - Artist cache table
  - Filter tables
- **Indexes**
  - File hash indexes
  - Artist name indexes
  - Path component indexes

## User Interface Layer

### 1. CLI Interface (`ui/cli.py`)
- Command parsing
- Option handling
- Rich output formatting
- Progress display
- Tree view visualization
- Database preview

## Type System

### 1. Core Types
- **Audio Types** (`core/mutagen_types.py`)
  - Mutagen integration types
  - Audio file protocols
  - Tag type definitions

- **Language Types** (`core/langid_types.pyi`)
  - Language detection types
  - Type stubs
  - Integration interfaces

### 2. Data Models
- **Track Metadata** (`core/metadata.py`)
  - Audio metadata representation
  - Required fields
  - Optional attributes

- **Process Results** (`core/processor.py`)
  - Operation outcomes
  - Error information
  - State tracking
  - File hash information

## Module Dependencies

### 1. Core Dependencies
```
core/processor.py
  ├── core/metadata_extractor.py
  │     ├── core/metadata.py
  │     └── core/mutagen_types.py
  ├── core/operations/
  │     ├── organize.py
  │     └── preview.py
  ├── core/path_generator.py
  │     └── core/path_components.py
  └── core/renaming_logic.py
        ├── core/sanitizer.py
        └── db/dao_artist_cache.py
```

### 2. Data Dependencies
```
db/db_manager.py
  ├── db/migrations/
  │     └── 001_initial.sql
  ├── db/dao_processing_before.py
  ├── db/dao_processing_after.py
  ├── db/dao_albums.py
  ├── db/dao_artist_cache.py
  ├── db/dao_filter.py
  └── db/dao_path_components.py
```

## Error Handling

### 1. Error Categories
- **Validation Errors**
  - Metadata validation
  - Path validation
  - Format validation
  - File hash validation

- **Processing Errors**
  - File operations
  - Database operations
  - State management
  - Cache operations

### 2. Error Recovery
- Transaction rollback
- State cleanup
- Error reporting
- Partial success handling
- Skip processed files

## Performance Optimization

### 1. Caching
- Artist ID caching (IDs up to 5 chars)
- Path component caching
- File hash caching
- Filter result caching

### 2. Database Optimization
- File hash indexing
- Batch operations
- Transaction management
- Skip already processed files
