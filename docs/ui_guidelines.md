# OMYM UI Guidelines

## Overview
This document defines the visual and interactive design principles for OMYM's command-line interface, ensuring a consistent and user-friendly experience.

## Command Line Interface (CLI)

### 1. Command Structure
```bash
omym MUSIC_PATH [options]

# Examples
omym path/to/music --dry-run    # Preview changes
omym path/to/music --target /output/path  # Process with custom target
omym path/to/music --db         # Show database operations
```

### 2. Command Options
- **Required Arguments**
  - `MUSIC_PATH`: Path to music file or directory to process

- **Common Options**
  - `--dry-run`: Preview changes without applying them
  - `--verbose`: Show detailed processing information
  - `--quiet`: Suppress all output except errors
  - `--force`: Override safety checks

- **Path Options**
  - `--target TARGET_PATH`: Target directory for organized files (defaults to MUSIC_PATH)

- **Additional Options**
  - `--config FILE`: Path to custom configuration file
  - `--db`: Enable database operations preview

### 3. Output Formatting

#### 3.1 Color Scheme
- **Headers**
  - Section titles: Bold Magenta
  - Table titles: Bold White

- **Path Components**
  - Source paths: Blue
  - Target paths: Blue
  - File names: Default color

- **Status Colors**
  - Success: Green
  - Warning: Yellow
  - Error: Red
  - Info: Cyan

#### 3.2 Tables
- **Artist Cache Table**
  - Artist Name: Cyan
  - Artist ID: Green
  - Operation: Yellow

- **Processing Tables**
  - File Hash: Cyan (no wrap)
  - Source/Target Path: Blue
  - Metadata: Green
  - Status: Yellow/Red

#### 3.3 Tree View
- Directory icons: 📁
- Success icons: ✅
- Error icons: ❌
- Preview icons: ✨

### 4. Progress Display

#### 4.1 Operation Progress
- File count summary
- Processing status updates
- Success/failure counts
- Error details for failed operations

#### 4.2 Preview Mode
- Tree view of planned changes
- Database operations preview (with --db)
- Warning and error notifications
- Operation summary

## Error Presentation

### 1. Error Messages
- Error type identification
- Detailed error description
- File path information
- Suggested resolution (when applicable)

### 2. Warning Messages
- Non-critical issues
- Processing anomalies
- Skipped files notification
- Performance suggestions

## Logging System

### 1. Log Levels
- **ERROR**: Critical failures
- **WARNING**: Non-critical issues
- **INFO**: Operation progress
- **DEBUG**: Detailed information (verbose mode)

### 2. Log Format
- Log level indicator
- Operation description
- File paths (when relevant)
- Error details (when applicable)

### 3. Log Output
- Console output with rich formatting
- Color-coded by severity
- Progress indicators
- Summary statistics

## Best Practices

### 1. Command Usage
- Always use --dry-run first
- Check database preview with --db
- Use --verbose for troubleshooting
- Use --force with caution

### 2. Error Handling
- Review all error messages
- Check file permissions
- Verify target paths
- Monitor database operations

### 3. Performance
- Monitor processing progress
- Review operation summaries
- Check for skipped files
- Watch for database warnings 