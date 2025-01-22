# OMYM (Organize My Music)

A Python tool to organize your music library by automatically processing metadata and organizing files into a consistent structure.

## Installation

```bash
git clone https://github.com/muray0196/omym.git
cd omym
pip install .
```

## Basic Usage

Organize your music folder:
```bash
omym organize /path/to/music/folder
```

Preview changes without moving files:
```bash
omym organize --dry-run /path/to/music/folder
```

## Features

- Supports MP3, FLAC, M4A/AAC, DSF formats
- Extracts and processes music metadata
- Creates organized folder structure
- Handles multi-disc albums and compilations
- Sanitizes filenames for cross-platform compatibility

## Configuration

Set up using environment variables:

```env
OMYM_OUTPUT_DIR=/path/to/organized/music
OMYM_FILE_FORMAT="{artist}/{album}/{track} - {title}"
OMYM_LOG_LEVEL=INFO
```
