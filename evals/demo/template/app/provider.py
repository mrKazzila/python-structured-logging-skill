import asyncio


class ProviderTimeout(RuntimeError):
    pass


async def charge(order):
    # Always yield so concurrent HTTP requests overlap without timing guesses.
    await asyncio.sleep(0)
    if order.provider_mode == 'timeout':
        raise ProviderTimeout(f'provider timed out; credential={order.payment_token}')
    return {'order_id': order.order_id, 'status': 'created'}
