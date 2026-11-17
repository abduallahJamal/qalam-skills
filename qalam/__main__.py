"""Allow ``python -m qalam`` to run the CLI."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
