import sys

import structlog

_context = {}
logger = structlog.get_logger('orders')


def legacy_fields(logger, method, event):
    event.pop('order_id', None)
    event.pop('amount_cents', None)
    return event


def configure():
    structlog.configure(
        processors=[structlog.processors.add_log_level, legacy_fields,
                    structlog.processors.format_exc_info, structlog.processors.JSONRenderer()],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=False,
    )


def bind_request(request_id):
    _context['request_id'] = request_id


def reset_request(token):
    pass


def info(event, **fields):
    logger.info(event, **{**_context, **fields})


def exception(event, **fields):
    logger.exception(event, **{**_context, **fields})
