"""BookWise — Smart Book Discovery & Recommendation System.

Run from the project folder:

    python main.py
"""

import logging
import sys

from src.cli.cli_app import BookWiseCLI
from src.data.data_manager import DatasetError
from src.services import BookWiseService
from src.utils.helpers import setup_logging


def main() -> int:
    setup_logging()
    try:
        service = BookWiseService()
    except DatasetError as error:
        print(f"\nBookWise could not start: {error}")
        return 1

    try:
        BookWiseCLI(service).run()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C or Ctrl+D: leave quietly instead of printing a stack trace.
        print("\n\nGoodbye!")
    except Exception:  # noqa: BLE001 - last safety net; details go to logs/bookwise.log
        logging.getLogger(__name__).exception("Unexpected error")
        print("\nSorry, something unexpected went wrong. Details were written to logs/bookwise.log.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
