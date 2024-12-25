User Guide
==========

Welcome to the OMYM User Guide! This guide will help you get started with organizing your music library using OMYM.

What is OMYM?
-----------

OMYM (Organize My Music) is a command-line tool that helps you organize your music library by:

- Analyzing music file metadata (artist, album, track numbers, etc.)
- Creating a consistent directory structure based on your preferences
- Handling multi-disc albums and various audio formats
- Preserving your music files while organizing them
- Providing a preview mode to review changes before applying them

Supported Features
---------------

Audio Formats:
- MP3 (.mp3)
- FLAC (.flac)
- M4A (.m4a)
- DSF (.dsf)

Metadata Fields:
- Artist and Album Artist
- Album Name
- Track Title
- Track Number
- Disc Number
- Year
- Genre

Organization Options:
- Customizable directory structure
- File naming patterns
- Multi-disc album handling
- Artist name consistency
- Preview mode for safety

Getting Started
-------------

1. Installation
   - Requirements: Python 3.8 or later
   - Install using pip: `pip install omym`

2. Basic Usage
   - Organize a directory: `omym organize /path/to/music`
   - Preview changes: `omym preview /path/to/music`
   - Get help: `omym --help`

3. Configuration
   - Set output directory: `OMYM_OUTPUT_DIR`
   - Set file format: `OMYM_FILE_FORMAT`
   - Set log level: `OMYM_LOG_LEVEL`

Example Usage
-----------

1. Preview organization:
   ```bash
   omym preview ~/Music
   ```

2. Organize with custom format:
   ```bash
   omym organize ~/Music --format "{artist}/{album} ({year})/{track:02d} {title}"
   ```

3. Organize to specific output directory:
   ```bash
   export OMYM_OUTPUT_DIR=~/OrganizedMusic
   omym organize ~/Music
   ```

Format Variables
-------------

Available variables for path formatting:

- `{artist}`: Artist name
- `{album_artist}`: Album artist name
- `{album}`: Album name
- `{track}`: Track number
- `{disc}`: Disc number
- `{title}`: Track title
- `{year}`: Release year
- `{genre}`: Genre

Format Modifiers:
- `:02d`: Zero-pad numbers (e.g., "01" instead of "1")
- `:s`: Convert to safe filename

Safety Features
-------------

OMYM includes several safety features:

1. Preview Mode
   - See all changes before they happen
   - No files are modified
   - Detailed report of planned changes

2. File Preservation
   - Original files are never modified
   - Files are copied, not moved
   - Source files remain untouched

3. Error Handling
   - Graceful handling of missing metadata
   - Clear error messages
   - Safe failure modes

4. Validation
   - Path format validation
   - Metadata validation
   - Destination path checking

Getting Help
----------

If you encounter any issues:

1. Check the error message for specific details
2. Use `--verbose` for more detailed output
3. Check the log file for technical details
4. File an issue on GitHub if needed

Next Steps
---------

- Read the Configuration guide for detailed setup options
- Check the Examples for common use cases
- See Troubleshooting for help with common issues

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quickstart
   installation
   usage
   configuration
   troubleshooting 