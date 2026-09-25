"""Public facade: configure(), scope(**fields), info/warning/exception(event, **fields)."""
import json
import logging
import sys
from contextlib import contextmanager

_context = {}
logger = logging.getLogger('consumer')


class Formatter(logging.Formatter):
    def format(self, record):
        result = {'event': record.getMessage(), 'level': record.levelname.lower()}
        result.update(getattr(record, 'fields', {}))
        if record.exc_info:
            result['exception'] = self.formatException(record.exc_info)
        return json.dumps(result)


def configure():
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(Formatter())
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)


@contextmanager
def scope(**fields):
    _context.update(fields)
    yield


def info(event, **fields):
    logger.info(event, extra={'fields': {**_context, **fields}})


def warning(event, **fields):
    logger.warning(event, extra={'fields': {**_context, **fields}})


def exception(event, **fields):
    logger.exception(event, extra={'fields': {**_context, **fields}})
