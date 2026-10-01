import asyncio


class RetryableError(Exception):
    pass


class PoisonError(Exception):
    pass


class Dependency:
    def __init__(self):
        self.calls = []
        self.started = asyncio.Event()

    async def execute(self, message):
        self.calls.append((message.message_id, message.attempt))
        self.started.set()
        await asyncio.sleep(0)
        mode = message.payload.get('mode', 'success')
        if mode == 'cancel':
            await asyncio.Event().wait()
        if mode == 'retry' and message.attempt < 2:
            raise RetryableError('upstream credential=SYNTHETIC_DEPENDENCY_SECRET')
        if mode == 'exhausted':
            raise RetryableError('SYNTHETIC_BARE_SECRET')
        if mode == 'poison':
            raise PoisonError('invalid payload SYNTHETIC_PAYLOAD_SECRET')
        if mode == 'unexpected':
            raise RuntimeError('SYNTHETIC_BARE_SECRET')
        return {'message_id': message.message_id, 'amount_cents': message.payload['amount_cents']}

    async def audit(self, message):
        await asyncio.sleep(0)
        if message.payload.get('audit_fail'):
            raise RuntimeError('SYNTHETIC_AUDIT_SECRET')
        return message.message_id
