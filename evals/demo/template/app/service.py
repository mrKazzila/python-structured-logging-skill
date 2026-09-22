from . import observability as log
from .provider import ProviderTimeout, charge


async def create_order(order):
    log.info(f'order_{order.order_id}_accepted', payload=order.model_dump())
    try:
        result = await charge(order)
    except ProviderTimeout:
        log.exception('order.failed', order_id=order.order_id, retryable=True)
        raise
    log.info('order.created', order_id=order.order_id, amount_cents=order.amount_cents)
    return result
