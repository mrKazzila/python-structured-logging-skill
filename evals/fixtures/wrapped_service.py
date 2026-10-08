import json
import sys


class EventLogger:
    """Project facade: callers pass a mapping, not logging keyword arguments."""

    def emit(self, level, event, fields):
        print(json.dumps({'level': level, 'event': event, **fields}), file=sys.stderr)


logger = EventLogger()


def process_invoice(invoice_id, amount_cents):
    logger.emit('info', 'invoice.processed', {'invoice_id': invoice_id})
    return amount_cents
