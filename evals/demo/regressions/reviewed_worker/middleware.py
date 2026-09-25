from time import perf_counter
from uuid import uuid4

from . import observability as log


class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        request_id = headers.get(b'x-request-id', b'').decode() or str(uuid4())
        token = log.bind_request(request_id)
        status = 500
        started = perf_counter()

        async def send_response(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
                message = {**message, 'headers': [
                    *message.get('headers', []),
                    (b'x-request-id', request_id.encode()),
                ]}
            await send(message)

        try:
            await self.app(scope, receive, send_response)
        except Exception:
            # Handled provider failures never reach this boundary.
            log.exception('request.failed', status_code=status)
            raise
        finally:
            try:
                route = scope.get('route')
                log.info(
                    'request.completed', status_code=status,
                    path=getattr(route, 'path', None),
                    duration_ms=round((perf_counter() - started) * 1000, 3),
                )
            finally:
                log.reset_request(token)
