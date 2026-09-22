from . import observability as log
from .provider import charge


async def create_order(order):
    result = await charge(order)
    log.info('order.created', order_id=order.order_id, amount_cents=order.amount_cents)
    return result
