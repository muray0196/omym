# OMYM (Organize My Music)

A Python tool to organize your music library by automatically renaming files and creating a consistent directory structure based on audio file metadata.

## Features

- Automatic metadata extraction from audio files (FLAC/MP3/M4A/DSF)
- Intelligent file and directory naming based on track, album, and artist information
- Consistent directory structure organization
- Smart artist ID generation with transliteration support
- Configuration management and logging
- Both CLI and GUI interfaces (GUI coming soon)

## Installation

1. Ensure you have Python 3.13 or later installed
2. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/omym.git
   cd omym
   ```
3. Install using pip:
   ```bash
   pip install .
   ```

## Usage

### Command Line Interface

Basic usage:
```bash
omym --base-path /path/to/music/library
```

Additional options:
```bash
omym --help  # Show all available options
omym --base-path /path/to/music --log-file /path/to/log.txt  # Specify log file
omym --config-file /path/to/config.json  # Use custom config file
```

### Configuration

The default configuration file is stored at `~/.config/omym/config.json`. You can specify:
- Base path for your music library
- Log file location
- Other settings (more coming soon)

## Development

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Run tests:
   ```bash
   pytest
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
