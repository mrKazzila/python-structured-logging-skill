"""External subprocess probe. Never copied into the agent's demo project."""

import asyncio
import contextlib
import importlib.metadata
import io
import json
import platform
import sys
import traceback
from pathlib import Path
from types import SimpleNamespace


def run(project):
    sys.path.insert(0, str(project))
    stdout, stderr = io.StringIO(), io.StringIO()
    usage = {'stdlib': 0, 'structlog': 0}
    responses = []

    def profile(frame, event, arg):
        if event != 'call':
            return
        filename = frame.f_code.co_filename.replace('\\', '/')
        name = frame.f_code.co_name
        if filename.endswith('/logging/__init__.py') and name == '_log':
            usage['stdlib'] += 1
        if '/structlog/' in filename and name == '_proxy_to_logger':
            usage['structlog'] += 1

    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        from httpx import ASGITransport, AsyncClient
        from app.main import app
        from app import observability as log
        from app.provider import charge

        async def exercise():
            async with AsyncClient(transport=ASGITransport(app=app), base_url='http://demo') as client:
                async def request(label, path, *, order_id=None, mode='success', request_id=None, amount=100):
                    headers = {'Authorization': 'Bearer TEST_SECRET_HEADER'}
                    if request_id:
                        headers['X-Request-ID'] = request_id
                    if order_id:
                        response = await client.post(path, headers=headers, json={
                            'order_id': order_id, 'amount_cents': amount,
                            'provider_mode': mode, 'payment_token': 'TEST_SECRET_PAYMENT',
                        })
                    else:
                        response = await client.get(path, headers=headers)
                    responses.append({
                        'label': label, 'status': response.status_code, 'body': response.json(),
                        'request_id': response.headers.get('x-request-id'),
                        'expected_request_id': request_id, 'order_id': order_id,
                        'amount_cents': amount, 'mode': mode,
                    })
                    # Same coroutine as the ASGI request: detects leaked context that
                    # a separate task/client wrapper could inadvertently conceal.
                    log.info('demo.probe', probe_id=label)

                await request('health', '/health')
                await request('success', '/orders', order_id='order-alpha', request_id='req-alpha')
                await request('failure', '/orders', order_id='order-beta', mode='timeout', request_id='req-beta')
                await request('invalid', '/orders', order_id='order-invalid', amount=-1, request_id='req-invalid')
                await asyncio.gather(
                    request('parallel_success', '/orders', order_id='order-parallel-a', request_id='req-parallel-a'),
                    request('parallel_failure', '/orders', order_id='order-parallel-b', mode='timeout', request_id='req-parallel-b'),
                )
                provider_success = await charge(SimpleNamespace(
                    order_id='direct', amount_cents=100, provider_mode='success',
                    payment_token='TEST_SECRET_PAYMENT'))
                try:
                    await charge(SimpleNamespace(order_id='direct', amount_cents=100,
                                                 provider_mode='timeout', payment_token='TEST_SECRET_PAYMENT'))
                except Exception as exc:
                    provider_failure = {'type': type(exc).__name__, 'message': str(exc)}
                else:
                    provider_failure = None
                return {'success': provider_success, 'failure': provider_failure}

        sys.setprofile(profile)
        try:
            provider = asyncio.run(exercise())
        finally:
            sys.setprofile(None)
    versions = {'python': platform.python_version()}
    for package in ('fastapi', 'starlette', 'pydantic', 'httpx', 'structlog', 'uvicorn'):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return {'responses': responses, 'stdout': stdout.getvalue(), 'stderr': stderr.getvalue(),
            'backend_calls': usage, 'versions': versions, 'provider': provider}


if __name__ == '__main__':
    try:
        print(json.dumps({'observations': run(Path(sys.argv[1]).resolve())}))
    except Exception:
        print(json.dumps({'error': traceback.format_exc()}))
        raise SystemExit(2)
