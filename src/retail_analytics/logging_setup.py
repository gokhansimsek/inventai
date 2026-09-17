"""Logging: readable lines on the console, JSON lines in the run folder.

Structured fields are passed with ``extra=`` (e.g. ``rule_id``, ``table``,
``rows_in``) and appear as top-level keys in the JSON file, so other tools can
consume a run's log without parsing messages.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

PACKAGE_LOGGER = "retail_analytics"
_STANDARD_ATTRIBUTES = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Format each record as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        """Render a log record as JSON.

        Args:
            record (logging.LogRecord): The record to render.

        Returns:
            str: A JSON object with ``timestamp``, ``level``, ``logger``, ``message``
                and every field passed through ``extra``.
        """
        event = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        event.update({k: v for k, v in vars(record).items() if k not in _STANDARD_ATTRIBUTES})
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, default=str)


def configure_logging(log_file: Path) -> None:
    """Send package logs to the console and to a JSON-lines file.

    Replaces handlers from any earlier call, so repeated runs in one process do not
    duplicate output.

    Args:
        log_file (Path): JSON-lines file to write; its folder is created if missing.
    """
    logger = logging.getLogger(PACKAGE_LOGGER)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())

    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
