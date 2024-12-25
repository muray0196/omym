Troubleshooting Guide
==================

This guide helps you diagnose and fix common issues with OMYM.

Installation Issues
----------------

Python Version Error
~~~~~~~~~~~~~~~~~

**Problem**: Error about Python version requirement

**Solution**:
1. Check your Python version:
   
   .. code-block:: bash

       python --version

2. Install Python 3.13 or higher
3. Ensure you're using the correct Python environment

Dependency Errors
~~~~~~~~~~~~~~

**Problem**: Missing or conflicting dependencies

**Solution**:
1. Use uv for installation:
   
   .. code-block:: bash

       uv pip install omym

2. Install in a fresh virtual environment:
   
   .. code-block:: bash

       uv venv
       source .venv/bin/activate
       uv pip install omym

Database Issues
-------------

Connection Errors
~~~~~~~~~~~~~~

**Problem**: Cannot connect to database

**Solution**:
1. Check database path:
   
   .. code-block:: bash

       echo $OMYM_DB_PATH

2. Ensure directory permissions:
   
   .. code-block:: bash

       chmod 755 /path/to/database/directory

3. Verify SQLite installation:
   
   .. code-block:: bash

       sqlite3 --version

Corruption Issues
~~~~~~~~~~~~~~

**Problem**: Database corruption messages

**Solution**:
1. Backup current database
2. Reset the database:
   
   .. code-block:: bash

       omym reset

3. Reprocess your files

Metadata Issues
-------------

Missing Metadata
~~~~~~~~~~~~~

**Problem**: Files not processed due to missing metadata

**Solution**:
1. Check file metadata:
   
   .. code-block:: bash

       omym inspect /path/to/file.mp3

2. Add missing metadata using a tag editor
3. Use ``--force`` to process anyway:
   
   .. code-block:: bash

       omym organize --force /path/to/music

Invalid Characters
~~~~~~~~~~~~~~~

**Problem**: Error processing file names with special characters

**Solution**:
1. Enable character mapping:
   
   .. code-block:: toml

       [paths]
       sanitize_names = true

2. Add custom character mappings:
   
   .. code-block:: toml

       [paths.mapping]
       "?" = ""
       "/" = "-"

File System Issues
---------------

Permission Errors
~~~~~~~~~~~~~~

**Problem**: Cannot read/write files

**Solution**:
1. Check file permissions:
   
   .. code-block:: bash

       ls -l /path/to/music

2. Fix permissions:
   
   .. code-block:: bash

       chmod -R u+rw /path/to/music

3. Run as appropriate user

Path Length Issues
~~~~~~~~~~~~~~~

**Problem**: Path too long errors

**Solution**:
1. Use shorter format strings:
   
   .. code-block:: bash

       omym organize --format "{artist:.30}/{album:.30}" /path/to/music

2. Enable long path support (Windows):
   
   .. code-block:: toml

       [paths]
       enable_long_paths = true

Performance Issues
---------------

Slow Processing
~~~~~~~~~~~~

**Problem**: Processing is unusually slow

**Solution**:
1. Enable caching:
   
   .. code-block:: toml

       [cache]
       enabled = true
       max_size = 1000

2. Optimize database:
   
   .. code-block:: bash

       omym optimize-db

3. Process in smaller batches

Memory Usage
~~~~~~~~~~

**Problem**: High memory usage

**Solution**:
1. Reduce cache size:
   
   .. code-block:: toml

       [cache]
       max_size = 500

2. Process directories sequentially:
   
   .. code-block:: bash

       for dir in */; do
           omym organize "$dir"
       done

Japanese Text Issues
-----------------

Romanization Problems
~~~~~~~~~~~~~~~~~

**Problem**: Incorrect romanization of Japanese text

**Solution**:
1. Configure Japanese settings:
   
   .. code-block:: toml

       [japanese]
       use_romaji = true
       preserve_spaces = true

2. Add custom mappings:
   
   .. code-block:: toml

       [japanese.mapping]
       "々" = "々"
       "ヶ" = "ケ"

Logging and Debugging
------------------

Enable Debug Logging
~~~~~~~~~~~~~~~~

To get more detailed logs:

1. Set log level:
   
   .. code-block:: bash

       export OMYM_LOG_LEVEL=DEBUG

2. Specify log file:
   
   .. code-block:: bash

       export OMYM_LOG_FILE=/path/to/omym.log

3. Run with verbose output:
   
   .. code-block:: bash

       omym organize -v /path/to/music

Common Error Messages
-----------------

"No such table"
~~~~~~~~~~~~

**Problem**: Database table missing

**Solution**:
1. Reset database:
   
   .. code-block:: bash

       omym reset

2. Rerun migrations:
   
   .. code-block:: bash

       omym migrate

"Invalid track position"
~~~~~~~~~~~~~~~~~~~

**Problem**: Track number metadata issues

**Solution**:
1. Check track metadata:
   
   .. code-block:: bash

       omym inspect /path/to/file.mp3

2. Fix track numbers in metadata
3. Use ``--ignore-track-position`` flag 