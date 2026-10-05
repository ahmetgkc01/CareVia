import json
import logging

from config.logging import JsonFormatter


def test_json_formatter_emits_machine_readable_event():
    record = logging.LogRecord(
        name="carevia.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="health check passed",
        args=(),
        exc_info=None,
    )

    event = json.loads(JsonFormatter().format(record))

    assert event["level"] == "INFO"
    assert event["logger"] == "carevia.test"
    assert event["message"] == "health check passed"
    assert "timestamp" in event
