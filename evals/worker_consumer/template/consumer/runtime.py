import asyncio
import logging
from . import observability as log

runtime_log = logging.getLogger('broker.runtime')


async def run(consumer, messages):
    """Unexpected errors reach runtime; it requeues. Cancellation stays unacked."""
    runtime_log.info('consumer started')
    results = await asyncio.gather(*(consumer.handle(m) for m in messages), return_exceptions=True)
    for message, result in zip(messages, results):
        if isinstance(result, Exception):
            consumer.broker.retry(message)
            runtime_log.error('consumer failed: %s', result,
                              exc_info=(type(result), result, result.__traceback__))
    await consumer.drain()
    runtime_log.info('consumer stopped')
    return results
