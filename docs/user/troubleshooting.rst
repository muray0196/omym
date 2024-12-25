Troubleshooting Guide
==================

This guide helps you resolve common issues when using OMYM.

Common Issues
-----------

Missing Metadata
~~~~~~~~~~~~~

Problem:
    Files are skipped or incorrectly organized due to missing metadata.

Solutions:
1. Check the original files have proper metadata
2. Use a metadata editor to add missing information
3. Use a more lenient format pattern
4. Check the log file for specific issues

Example:
    .. code-block:: bash

        export OMYM_LOG_LEVEL=DEBUG
        omym preview ~/Music

File Access Issues
~~~~~~~~~~~~~~~

Problem:
    Permission denied or cannot access files.

Solutions:
1. Check file permissions
2. Verify directory permissions
3. Run with appropriate user rights
4. Check file ownership

Example:
    .. code-block:: bash

        ls -l ~/Music
        chmod -R u+r ~/Music

Path Length Issues
~~~~~~~~~~~~~~

Problem:
    File paths are too long for the filesystem.

Solutions:
1. Use shorter format patterns
2. Reduce nested directory levels
3. Use abbreviated metadata
4. Consider filesystem limitations

Example:
    .. code-block:: bash

        # Instead of
        export OMYM_FILE_FORMAT="{artist}/{album} ({year})/{disc:02d}-{track:02d} {title}"
        # Use
        export OMYM_FILE_FORMAT="{artist}/{album}/{track:02d} {title}"

Special Characters
~~~~~~~~~~~~~~~

Problem:
    Invalid characters in filenames or paths.

Solutions:
1. Use the :s modifier for safe filenames
2. Check for unsupported characters
3. Use simpler format patterns
4. Enable automatic character replacement

Example:
    .. code-block:: bash

        export OMYM_FILE_FORMAT="{artist:s}/{album:s}/{track:02d} {title:s}"

Multi-disc Albums
~~~~~~~~~~~~~~

Problem:
    Incorrect handling of multi-disc albums.

Solutions:
1. Use disc number in format
2. Check disc metadata
3. Verify album grouping
4. Use appropriate separators

Example:
    .. code-block:: bash

        export OMYM_FILE_FORMAT="{artist}/{album}/Disc {disc:02d}/{track:02d} {title}"

Compilation Albums
~~~~~~~~~~~~~~

Problem:
    Various artists albums not organized correctly.

Solutions:
1. Use album_artist instead of artist
2. Check compilation flags
3. Verify artist metadata
4. Use appropriate format pattern

Example:
    .. code-block:: bash

        export OMYM_FILE_FORMAT="{album_artist}/{album}/{track:02d} {artist} - {title}"

Database Issues
~~~~~~~~~~~~

Problem:
    Database errors or corruption.

Solutions:
1. Check database permissions
2. Verify database path
3. Ensure sufficient disk space
4. Reset database if necessary

Example:
    .. code-block:: bash

        rm ~/.local/share/omym/omym.db
        omym organize ~/Music

Performance Issues
~~~~~~~~~~~~~~

Problem:
    Slow processing or high resource usage.

Solutions:
1. Process smaller batches
2. Use simpler format patterns
3. Check disk space
4. Monitor system resources

Example:
    .. code-block:: bash

        omym organize ~/Music/Album1
        omym organize ~/Music/Album2

Debugging
--------

Enable Debug Logging
~~~~~~~~~~~~~~~~

Get detailed information about issues:

.. code-block:: bash

    export OMYM_LOG_LEVEL=DEBUG
    omym organize ~/Music

Check Log File
~~~~~~~~~~~

View the log file for details:

.. code-block:: bash

    cat ~/.local/share/omym/omym.log

Use Preview Mode
~~~~~~~~~~~~

Test changes before applying:

.. code-block:: bash

    omym preview ~/Music

Use Verbose Output
~~~~~~~~~~~~~~

Get more detailed output:

.. code-block:: bash

    omym organize --verbose ~/Music

Common Error Messages
-----------------

"Missing Required Metadata"
~~~~~~~~~~~~~~~~~~~~~~~

Cause:
    Required metadata fields are missing.

Solution:
1. Check file metadata
2. Use metadata editor
3. Modify format pattern
4. Check log for details

"Permission Denied"
~~~~~~~~~~~~~~~

Cause:
    Insufficient file permissions.

Solution:
1. Check file ownership
2. Verify directory permissions
3. Run with appropriate rights
4. Use sudo if necessary

"Invalid Format Pattern"
~~~~~~~~~~~~~~~~~~

Cause:
    Format string syntax error.

Solution:
1. Check format syntax
2. Verify variable names
3. Check modifier usage
4. Test with preview mode

"Database Error"
~~~~~~~~~~~~

Cause:
    Database access or corruption issues.

Solution:
1. Check permissions
2. Verify disk space
3. Reset database
4. Check log file

Getting Help
----------

If you still have issues:

1. Check Documentation
   - Read relevant guides
   - Review format patterns
   - Check configuration options

2. Search Issues
   - Look for similar problems
   - Check resolved issues
   - Review workarounds

3. Report Problems
   - Provide error messages
   - Include log output
   - Describe steps to reproduce
   - Share configuration

4. Contact Support
   - Open GitHub issue
   - Provide system details
   - Share log files
   - Describe use case 