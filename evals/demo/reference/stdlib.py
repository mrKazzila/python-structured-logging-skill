import json
import logging
import sys
from contextvars import ContextVar

from .safe_output import configure_server, sanitize

_context = ContextVar('request_context', default={})
logger = logging.getLogger('orders')


class JsonFormatter(logging.Formatter):
    def format(self, record):
        result = {'event': record.getMessage(), 'level': record.levelname.lower(), **getattr(record, 'fields', {})}
        if record.exc_info:
            result['exception'] = self.formatException(record.exc_info)
        return json.dumps(sanitize(result))


def configure():
    configure_server()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False


def bind_request(request_id):
    return _context.set({'request_id': request_id})


def reset_request(token):
    _context.reset(token)


def info(event, **fields):
    logger.info(event, extra={'fields': {**_context.get(), **fields}})


def exception(event, **fields):
    logger.exception(event, extra={'fields': {**_context.get(), **fields}})
