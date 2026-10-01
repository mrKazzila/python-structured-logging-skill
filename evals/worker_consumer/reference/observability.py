"""Small calibration repair; never supplied to A/B workers."""
import json
import logging
import math
import sys
from contextlib import contextmanager
from contextvars import ContextVar

_context = ContextVar('context', default={})
logger = logging.getLogger('consumer')


def safe(value, depth=0):
    if depth > 8:
        return '[bounded]'
    if type(value) is dict:
        return {k:safe(v,depth+1) for k,v in list(value.items())[:50]
                if type(k) is str and k not in ('payload','body','payment_token','password','authorization')}
    if type(value) in (list,tuple):
        return [safe(v,depth+1) for v in value[:50]]
    if type(value) is float and not math.isfinite(value):
        return None
    if type(value) in (str,int,float,bool) or value is None:
        return value
    return '[unsupported]'


class Formatter(logging.Formatter):
    def format(self, record):
        try:
            result = {**safe(getattr(record,'fields',{})),
                      'event':record.msg if record.name=='consumer' else 'runtime.lifecycle',
                      'level':record.levelname.lower()}
            if record.exc_info:
                result['error_type']=record.exc_info[0].__name__
            return json.dumps(result,allow_nan=False)
        except Exception:
            return '{"event":"logging.fallback","level":"error"}'


def configure():
    handler=logging.StreamHandler(sys.stderr); handler.setFormatter(Formatter())
    root=logging.getLogger(); root.handlers=[handler]; root.setLevel(logging.INFO)
    logger.handlers=[]; logger.propagate=True; logger.setLevel(logging.INFO)


@contextmanager
def scope(**fields):
    token=_context.set({**_context.get(),**fields})
    try:
        yield
    finally:
        _context.reset(token)


def info(event,**fields):
    logger.info(event,extra={'fields':{**fields,**_context.get()}})


def warning(event,**fields):
    logger.warning(event,extra={'fields':{**fields,**_context.get()}})


def exception(event,**fields):
    logger.exception(event,extra={'fields':{**fields,**_context.get()}})
