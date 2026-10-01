import re
import json
import logging
import math
import sys


def sanitize(value, active=None):
    """Bounded demo normalization/redaction; not a general secret detector."""
    if active is None:
        active = set()
    if isinstance(value, (dict, list, tuple)):
        if id(value) in active or len(active) >= 32:
            return '[unsupported value]'
        active.add(id(value))
        try:
            if isinstance(value, dict):
                # Omit unsupported keys without invoking user str/repr methods.
                return {key: sanitize(item, active) for key, item in value.items()
                        if isinstance(key, str)}
            return [sanitize(item, active) for item in value]
        finally:
            active.remove(id(value))
    if isinstance(value, str):
        return re.sub(r'TEST_SECRET_[A-Z0-9_]+', '[REDACTED]', value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return '[unsupported value]'


class ServerFormatter(logging.Formatter):
    def format(self, record):
        event = {'event': 'server.log', 'level': record.levelname.lower(),
                 'message': record.getMessage()}
        if record.exc_info:
            event['exception'] = self.formatException(record.exc_info)
        return json.dumps(sanitize(event), allow_nan=False)


def configure_server():
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ServerFormatter())
    for name in ('uvicorn', 'uvicorn.error', 'uvicorn.access'):
        logger = logging.getLogger(name)
        logger.handlers = [handler]
        logger.propagate = False
