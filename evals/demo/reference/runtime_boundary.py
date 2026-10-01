"""Test oracle only: an outer boundary owns unexpected HTTP failures."""

from uuid import uuid4

from . import observability as log


class RuntimeBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        request_id = dict(scope['headers']).get(b'x-request-id', b'').decode() or str(uuid4())
        scope = {**scope, 'headers': [*scope['headers'], (b'x-request-id', request_id.encode())]}
        token = log.bind_request(request_id)
        started = False

        async def correlated_send(message):
            nonlocal started
            if message['type'] == 'http.response.start':
                started = True
                headers = [(key, value) for key, value in message.get('headers', [])
                           if key.lower() != b'x-request-id']
                message = {**message, 'headers': [*headers, (b'x-request-id', request_id.encode())]}
            await send(message)

        try:
            await self.app(scope, receive, correlated_send)
        except Exception:
            log.exception('request.failed', request_id=request_id)
            # Starlette already sent its 500; this boundary owns the outcome.
            if not started:
                raise
        finally:
            log.reset_request(token)
