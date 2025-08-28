# OMYM Tool Flow Documentation

## Overview
This document outlines the operational flow of the OMYM (Organize My Music) tool, detailing how users interact with the application and how different processes and modules are connected.

## User Interaction Flow

### 1. Entry Points
- **CLI Mode**
  - Basic command: `omym MUSIC_PATH`
  - Options:
    - `--target TARGET_PATH`: Target directory for organized files
    - `--dry-run`: Preview changes without applying them
    - `--verbose`: Show detailed processing information
    - `--quiet`: Suppress all output except errors
    - `--force`: Override safety checks
    - `--config FILE`: Path to custom configuration file
    - `--db`: Enable database operations preview
    - `--clear-artist-cache`: Clear cached artist IDs before processing
    - `--clear-cache`: Clear all caches and processing state before processing

### 2. Processing Phases

#### 2.1 Planning Phase
1. **Configuration Loading**
   - Load TOML configuration
   - Validate input paths
   - Initialize logging

2. **Database Preparation**
   - Initialize SQLite database
   - Apply pending migrations
   - Clear previous processing state

3. **File Discovery**
   - Scan input directories
   - Filter audio files (.mp3, .flac, .m4a, .dsf, .aac, .alac)
   - Calculate file hashes
   - Validate file accessibility

#### 2.2 Analysis Phase
1. **Metadata Extraction**
   - Read audio files using mutagen
   - Extract track metadata
   - Store in processing_before table with file hash

2. **Music Organization**
   - Group tracks by album
   - Process album metadata
   - Generate artist IDs (up to 5 characters)
   - Cache artist information

3. **Path Generation**
   - Generate directory structure
   - Generate file names with artist IDs
   - Validate path uniqueness
   - Store in processing_after table

#### 2.3 Execution Phase
1. **Preview Mode (--dry-run)**
   - Display planned changes in tree structure
   - Show file movements
   - Present warnings/errors
   - Show database operations preview (--db)

2. **Process Mode**
   - Create target directories
   - Move and rename files
   - Update database state
   - Clean up empty directories

## Module Interaction Flow

### 1. Core Processing Pipeline
```
[CLI] → [MusicProcessor]
  ↓         ↓
[Config] → [DatabaseManager]
            ↓
[MetadataExtractor] → [DirectoryGenerator]
       ↓                    ↓
[FileNameGenerator] ← [ArtistIdGenerator]
       ↓
[File Operations]
```

### 2. Database Operations Flow
```
[ProcessingBeforeDAO] → [Processing] → [ProcessingAfterDAO]
        ↓                    ↓               ↓
[ArtistCacheDAO] ← [CachedArtistIdGenerator] [Path Validation]
```

## Error Handling

### 1. Validation Errors
- Invalid file formats
- Missing required metadata
- Duplicate target paths
- Permission issues
- File hash conflicts

### 2. Processing Errors
- File access failures
- Database operation failures
- Path generation conflicts
- File system operation failures
- Metadata extraction errors

### 3. Recovery Mechanisms
- Transaction rollback for database operations
- Partial success handling
- Detailed error logging with file paths
- User notification with error details
- Skip already processed files

## Progress Tracking

### 1. CLI Progress
- File scanning progress
- Processing status updates
- Operation counts
- Error summaries with file paths
- Tree view of changes

### 2. Logging
- Operation timestamps
- Error details with stack traces
- Warning messages
- Success confirmations
- File movement logs

## Database State Management

### 1. Pre-Processing State (ProcessingBeforeDAO)
- File paths and hashes
- Raw metadata
- Initial validation results
- Processing status

### 2. Artist Cache (ArtistCacheDAO)
- Artist names
- Generated artist IDs (up to 5 chars)
- Cache hits/misses

### 3. Post-Processing State (ProcessingAfterDAO)
- Source and target paths
- File hashes
- Operation results
- Final validation status

## Performance Considerations

### 1. Database Optimization
- Indexed queries on file hashes
- Cached artist ID lookups
- Batch operations in transactions
- Skip already processed files

### 2. File Operations
- Atomic file moves
- Path validation caching
- Efficient directory creation
- Empty directory cleanup
- Hash-based file tracking
