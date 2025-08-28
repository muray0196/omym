# OMYM Technology Stack

## Overview
This document provides a comprehensive list of technologies, tools, and frameworks used in the OMYM project.

## Core Technologies

### 1. Programming Language
- **Python 3.13+**
  - Type hints (PEP 484)
  - Data classes (PEP 557)
  - Modern string handling
  - SQLite database integration

### 2. Core Dependencies

#### 2.1 Audio Processing
- **mutagen (>=1.47.0)**
  - Audio metadata extraction
  - Multiple format support (MP3, FLAC, M4A/AAC, DSF, Opus)
  - Tag manipulation

#### 2.2 Text Processing
- **pykakasi (>=2.3.0)**
  - Japanese text processing
  - Romanization support
  - Character conversion
- **langid (>=1.1.6)**
  - Language detection
  - Confidence scoring
- **unidecode (>=1.3.8)**
  - Unicode text normalization
  - ASCII conversion

#### 2.3 User Interface
- **rich (>=13.7.0)**
  - Terminal formatting
  - Progress bars
  - Tables and tree views
  - Colored output

### 3. Database Technology
- **SQLite3**
  - Local file-based database
  - SQL schema management
  - Migration support
  - Data Access Objects (DAOs)

## Development Tools

### 1. Build System
- **setuptools (>=61.0)**
  - Package management
  - Distribution
  - Resource handling

### 2. Testing Framework
- **pytest (>=8.3.4)**
  - Test framework
  - Fixture support
  - Parameterized testing
- **pytest-cov (>=4.1.0)**
  - Code coverage
  - Coverage reporting
- **pytest-mock (>=3.14.0)**
  - Mocking support
  - Test isolation

### 3. Code Quality
- **ruff**
  - Linting
  - Code formatting
  - Style enforcement
  - PEP 8 compliance
  - Configured line length: 120
  - Ignores: F401

### 4. Package Management
- **uv**
  - Dependency management
  - Virtual environment
  - Fast installation

## Documentation

### 1. Documentation Format
- **Markdown**
  - Project documentation
  - API documentation
  - Development guides

### 2. Code Documentation
- **Google Style Python Docstrings**
  - Function documentation
  - Type hints
  - Usage examples

## Architecture Patterns

### 1. Data Access
- Data Access Objects (DAO)
- Repository pattern
- SQL schema migrations

### 2. Command Pattern
- CLI commands
- Operation encapsulation
- Command-line parsing

### 3. Processing Pipeline
- Metadata extraction
- File organization
- Error handling
