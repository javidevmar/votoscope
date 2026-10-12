"""Logging configuration shared by every entrypoint.

Level comes from the LOG_LEVEL environment variable (default INFO); the
format is date, level, logger and message. Call ``configure_logging()``
once when an entrypoint starts.
"""

import logging
import os

DEFAULT_LEVEL = "INFO"
FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging() -> None:
    """Configure the root logger from LOG_LEVEL (default INFO)."""
    level_name = os.environ.get("LOG_LEVEL", DEFAULT_LEVEL).upper()
    level = logging.getLevelNamesMapping().get(level_name)
    if level is None:
        level = logging.INFO
        logging.basicConfig(level=level, format=FORMAT, force=True)
        logging.getLogger(__name__).warning(
            "invalid LOG_LEVEL=%r, using %s", level_name, DEFAULT_LEVEL
        )
        return
    logging.basicConfig(level=level, format=FORMAT, force=True)
