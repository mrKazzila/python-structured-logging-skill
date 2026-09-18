import logging

logger = logging.getLogger(__name__)


def charge(amount_cents):
    if amount_cents < 0:
        raise ValueError('negative amount')
    return amount_cents


def handle_invoice(invoice_id, amount_cents):
    try:
        result = charge(amount_cents)
    except ValueError:
        logger.exception('invoice.charge.failed', extra={'invoice_id': invoice_id})
        raise
    logger.info('invoice.charge.completed', extra={'invoice_id': invoice_id})
    return result
