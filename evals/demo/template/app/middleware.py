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
        log.info('request.received', authorization=headers.get(b'authorization', b'').decode())

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
        finally:
            log.info('request.completed', status_code=status, path=scope['path'])
            log.reset_request(token)
