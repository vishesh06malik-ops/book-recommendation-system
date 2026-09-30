"""Saving and loading JSON files safely.

Two problems this module solves:
1. A crash half-way through writing would leave a broken file. We therefore
   write to a temporary file first and then replace the real file in one step.
2. A corrupted file (edited by hand, disk error) must not crash the app.
   It is renamed to *.corrupt so no data is silently destroyed, and the
   caller receives the default value instead.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised when data cannot be written to disk."""


def load_json(path: Path, default: Any) -> Any:
    """Return the JSON content of `path`, or `default` if the file is missing or broken."""
    path = Path(path)
    if not path.exists():
        return default
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as error:
        backup = path.with_name(f"{path.name}.corrupt-{int(time.time())}")
        logger.error("Corrupted JSON in %s (%s); moved to %s", path, error, backup.name)
        try:
            path.rename(backup)
        except OSError:
            logger.exception("Could not back up corrupted file %s", path)
        return default
    except (OSError, UnicodeDecodeError) as error:
        logger.error("Could not read %s: %s", path, error)
        return default


def save_json(path: Path, data: Any) -> None:
    """Write `data` as pretty JSON using an atomic replace. Raises StorageError on failure."""
    path = Path(path)
    temp_path = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False, sort_keys=True)
        os.replace(temp_path, path)  # atomic on Windows, macOS and Linux
    except (OSError, TypeError, ValueError) as error:
        logger.error("Could not save %s: %s", path, error)
        raise StorageError("Your data could not be saved to disk.") from error
