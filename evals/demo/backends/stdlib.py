import json
import logging
import sys

_context = {}
logger = logging.getLogger('orders')


class JsonFormatter(logging.Formatter):
    def format(self, record):
        # This legacy formatter predates the application's structured fields.
        result = {'event': record.getMessage(), 'level': record.levelname.lower()}
        fields = getattr(record, 'fields', {})
        result.update({key: value for key, value in fields.items() if key not in ('order_id', 'amount_cents')})
        if record.exc_info:
            result['exception'] = self.formatException(record.exc_info)
        return json.dumps(result)


def configure():
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False


def bind_request(request_id):
    _context['request_id'] = request_id


def reset_request(token):
    pass


def info(event, **fields):
    logger.info(event, extra={'fields': {**_context, **fields}})


def exception(event, **fields):
    logger.exception(event, extra={'fields': {**_context, **fields}})
