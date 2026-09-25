import sys
from contextvars import ContextVar

import structlog

from .safe_output import configure_server, sanitize

_context = ContextVar('request_context', default={})
logger = structlog.get_logger('orders')


def safe_fields(logger, method, event):
    return sanitize(event)


def configure():
    configure_server()
    structlog.configure(
        processors=[structlog.processors.add_log_level, structlog.processors.format_exc_info,
                    safe_fields, structlog.processors.JSONRenderer()],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=False,
    )


def bind_request(request_id):
    return _context.set({'request_id': request_id})


def reset_request(token):
    _context.reset(token)


def info(event, **fields):
    logger.info(event, **{**_context.get(), **fields})


def exception(event, **fields):
    logger.exception(event, **{**_context.get(), **fields})
