import asyncio
from . import observability as log
from .dependency import RetryableError, PoisonError
from .service import process


class Consumer:
    def __init__(self, broker, dependency):
        self.broker = broker
        self.dependency = dependency
        self.background = []

    async def handle(self, message):
        with log.scope(message_id=message.message_id, correlation_id=message.correlation_id):
            log.info('message.received', payload=message.payload, attempt=message.attempt)
            try:
                result = await process(message, self.dependency)
            except RetryableError:
                if message.attempt < 3:
                    self.broker.retry(message)
                    log.exception('message.retry', attempt=message.attempt, retryable=True)
                    return 'retry'
                self.broker.dead_letter(message)
                log.exception('message.dead_letter', attempt=message.attempt, retryable=False)
                return 'dead_letter'
            except PoisonError:
                self.broker.dead_letter(message)
                log.exception('message.dead_letter', attempt=message.attempt, retryable=False)
                return 'dead_letter'
            except asyncio.CancelledError:
                log.exception('message.cancelled')
                raise
            except Exception:
                log.exception('message.failed')
                raise
            self.broker.ack(message)
            log.info('message.processed', amount_cents=result['amount_cents'], outcome='ack')
            self.background.append((message, asyncio.create_task(self.dependency.audit(message))))
            return result

    async def drain(self):
        pending, self.background = self.background, []
        for message, task in pending:
            try:
                await task
            except Exception:
                log.exception('audit.failed', message_id=message.message_id)
