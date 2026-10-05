import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Emit operational logs as single-line JSON without request bodies."""

    def format(self, record):
        event = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, ensure_ascii=False)
