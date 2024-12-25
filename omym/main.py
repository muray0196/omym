"""Main entry point for OMYM."""

from omym.ui.cli import main

# Make the main function available for testing
__main_block__ = main

if __name__ == "__main__":
    main()
