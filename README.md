# OMYM (Organize Music Your Music)

A Python tool that helps you organize your music library by automatically processing metadata and organizing files into a clean, consistent structure.

## Features

- **Smart Metadata Extraction**: Automatically reads metadata from your music files
  - Supported formats: MP3, FLAC, M4A/AAC, DSF
  - Extracts artist, album, track numbers, and more
  - Handles multi-disc albums correctly

- **Intelligent Organization**: Creates a clean folder structure based on metadata
  - Artist/Album/Track organization
  - Proper handling of album artists vs track artists
  - Special handling for compilations and various artists albums

- **File Management**:
  - Sanitizes filenames for cross-platform compatibility
  - Preserves your music files' metadata
  - Handles duplicate files intelligently
  - Groups tracks into albums based on metadata

## Installation

```bash
pip install omym
```

## Quick Start

1. Basic usage to organize a music folder:
```bash
omym organize /path/to/music/folder
```

2. Preview changes without moving files:
```bash
omym organize --dry-run /path/to/music/folder
```

3. Organize with custom settings:
```bash
omym organize --format "{artist}/{album} ({year})/{track} - {title}" /path/to/music/folder
```

## Configuration

OMYM can be configured using environment variables or a configuration file. Create a `.env` file in your working directory:

```env
OMYM_OUTPUT_DIR=/path/to/organized/music
OMYM_FILE_FORMAT="{artist}/{album}/{track} - {title}"
OMYM_LOG_LEVEL=INFO
```

## Available Format Variables

- `{artist}` - Track artist
- `{album_artist}` - Album artist (if different from track artist)
- `{album}` - Album name
- `{track}` - Track number (padded with zeros)
- `{title}` - Track title
- `{year}` - Release year
- `{disc}` - Disc number (for multi-disc albums)

## Examples

1. Basic organization:
```bash
omym organize ~/Music
```

2. Custom format with year in album folder:
```bash
omym organize --format "{artist}/{album} ({year})/{track} - {title}" ~/Music
```

3. Process specific file types:
```bash
omym organize --formats mp3,flac ~/Music
```

## Support

For bug reports and feature requests, please visit:
https://github.com/yourusername/omym/issues

## License

[Your License Here] 