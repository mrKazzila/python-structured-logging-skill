"""Application-owned stdlib JSON pipeline, also usable outside HTTP requests."""

from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import sys
import traceback

_context = ContextVar('logging_request_context', default=None)
logger = logging.getLogger('orders')
_SENSITIVE_KEYS = re.compile(r'authorization|cookie|credential|password|secret|token|api[_-]?key', re.I)
_SENSITIVE_TEXT = re.compile(
    r'(?i)\b(authorization|credential|password|secret|token|api[_-]?key)\s*[:=]\s*[^\r\n]*'
)
_RESERVED = frozenset(logging.makeLogRecord({}).__dict__) | {'message', 'asctime', 'fields'}


def _safe(value):
    """Defense in depth; callers still select fields instead of logging payloads."""
    if isinstance(value, dict):
        return {
            str(key): '[REDACTED]' if _SENSITIVE_KEYS.search(str(key)) else _safe(item)
            for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [_safe(item) for item in value]
    if isinstance(value, str):
        return _SENSITIVE_TEXT.sub(lambda match: match.group(1) + '=[REDACTED]', value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    # repr/str of arbitrary objects can expose payloads and credentials.
    return '[unsupported value]'


def _safe_exception(exc_info):
    """Retain traceback locations/types, never exception text, locals or source."""
    seen = set()

    def render(error, tb):
        if error is None or id(error) in seen:
            return []
        seen.add(id(error))
        lines = []
        cause = error.__cause__
        if cause is not None:
            lines.extend(render(cause, cause.__traceback__))
            lines.append('The above exception was the direct cause of the following exception:')
        elif error.__context__ is not None and not error.__suppress_context__:
            lines.extend(render(error.__context__, error.__context__.__traceback__))
            lines.append('During handling of the above exception, another exception occurred:')
        lines.append('Traceback (most recent call last):')
        for frame, lineno in traceback.walk_tb(tb):
            lines.append(f'  File "{Path(frame.f_code.co_filename).name}", line {lineno}, in {frame.f_code.co_name}')
        lines.append(f'{type(error).__name__}: [exception message omitted]')
        if isinstance(error, BaseExceptionGroup):
            for nested in error.exceptions:
                lines.extend(render(nested, nested.__traceback__))
        return lines

    return '\n'.join(render(exc_info[1], exc_info[2]))


class ContextFilter(logging.Filter):
    def filter(self, record):
        fields = dict(getattr(record, 'fields', {}))
        request_id = _context.get()
        if request_id is not None:
            fields['request_id'] = request_id
        record.fields = fields
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        fields = {key: value for key, value in record.__dict__.items() if key not in _RESERVED}
        fields.update(getattr(record, 'fields', {}))
        result = _safe(fields)
        # Fields cannot override the envelope or inject an unsanitized traceback.
        result.pop('exception', None)
        result.update({
            'event': _safe(record.getMessage()),
            'level': record.levelname.lower(),
            'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            'logger': record.name,
        })
        if record.exc_info and record.exc_info[1] is not None:
            result['exception'] = _safe_exception(record.exc_info)
        return json.dumps(result, allow_nan=False)


def configure():
    # Only manage our own handler; do not configure root or third-party loggers.
    for handler in logger.handlers:
        if getattr(handler, '_orders_json_handler', False):
            return
    handler = logging.StreamHandler(sys.stderr)
    handler._orders_json_handler = True
    handler.setFormatter(JsonFormatter())
    handler.addFilter(ContextFilter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def bind_request(request_id):
    return _context.set(request_id)


def reset_request(token):
    _context.reset(token)


def info(event, **fields):
    logger.info(event, extra={'fields': fields})


def exception(event, **fields):
    logger.exception(event, extra={'fields': fields})
