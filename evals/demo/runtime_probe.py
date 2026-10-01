"""Held-out real-server and public-facade probes, each in a fresh process.

stdout/stderr belong to the application. Metadata goes to a separate file so
logging diagnostics (including writes to file descriptors) cannot escape grading.
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


@contextmanager
def capture_streams():
    """Attribute synchronous emissions, including raw fd writes, to one call.

    Replay captured bytes to the original descriptors so the complete process
    streams remain authoritative too. No candidate logger internals are used.
    """
    observed = {}
    sys.stdout.flush()
    sys.stderr.flush()
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        saved = [os.dup(1), os.dup(2)]
        try:
            os.dup2(stdout.fileno(), 1)
            os.dup2(stderr.fileno(), 2)
            yield observed
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            for fd, original, stream, name in zip((1, 2), saved, (stdout, stderr), ('stdout', 'stderr')):
                os.dup2(original, fd)
                os.close(original)
                stream.seek(0)
                raw = stream.read()
                observed[name] = raw.decode('utf-8', errors='replace')
                while raw:
                    raw = raw[os.write(fd, raw):]


def formatter():
    from app import observability as log

    log.configure()
    logging.raiseExceptions = True  # Exercise stdlib's development diagnostic path.
    secret = 'TEST_SECRET_FORMATTER_' + uuid4().hex.upper()
    local_secret = 'TEST_SECRET_LOCAL_' + uuid4().hex.upper()
    class HostileKey:
        def __str__(self):
            raise RuntimeError(secret)

        def __repr__(self):
            return local_secret

    cycle = []
    cycle.append(cycle)
    cases = [('ordinary_object', object()), ('hostile_mapping_key', {HostileKey(): 'value'}),
             ('cycle', cycle), ('nan', float('nan')), ('positive_infinity', float('inf')),
             ('negative_infinity', float('-inf'))]
    observed = []
    for name, value in cases:
        raised = recovery_raised = None
        with capture_streams() as emission:
            try:
                raise RuntimeError(secret)
            except RuntimeError:
                try:
                    log.exception('demo.serialization', case=name, measurement=value)  # FORMATTER_SOURCE_SENTINEL
                except Exception as error:
                    raised = type(error).__name__
        with capture_streams() as recovery:
            try:
                log.info('demo.serialization_recovery', case=name)
            except Exception as error:
                recovery_raised = type(error).__name__
        observed.append({'case': name, 'raised': raised, 'recovery_raised': recovery_raised,
                         'emission': emission, 'recovery': recovery})
    return {'secrets': [secret, local_secret], 'cases': observed}


async def server():
    import httpx
    import uvicorn

    secret = 'TEST_SECRET_UNEXPECTED_' + uuid4().hex.upper()
    query_secret = 'TEST_SECRET_QUERY_' + uuid4().hex.upper()
    request_id = 'req-unexpected-' + uuid4().hex
    # Match the documented CLI: Uvicorn configures its logging before importing
    # app.main, allowing the project's configure() to own the final pipeline.
    config = uvicorn.Config('app.main:app', host='127.0.0.1', port=0,
                            access_log=True, http='h11', lifespan='on')
    config.load()
    from app.main import app

    async def unexpected():
        raise RuntimeError(secret)

    # Standard FastAPI routing API; outer ASGI wrappers may delegate to .app.
    router_app = app
    while not hasattr(router_app, 'add_api_route') and hasattr(router_app, 'app'):
        router_app = router_app.app
    router_app.add_api_route('/__evaluation_unexpected__', unexpected, methods=['GET'])
    ready = asyncio.Event()

    class ReadyServer(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            ready.set()

    instance = ReadyServer(config)
    task = asyncio.create_task(instance.serve())
    readiness = asyncio.create_task(ready.wait())
    try:
        done, _ = await asyncio.wait([task, readiness], return_when=asyncio.FIRST_COMPLETED)
        if task in done:
            await task
            raise RuntimeError('Uvicorn exited before readiness')
        port = instance.servers[0].sockets[0].getsockname()[1]
        async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
            response = await client.get(
                f'http://127.0.0.1:{port}/__evaluation_unexpected__',
                params={'credential': query_secret}, headers={'X-Request-ID': request_id})
        return {'status': response.status_code,
                'request_id': response.headers.get('x-request-id'),
                'expected_request_id': request_id, 'secrets': [secret, query_secret]}
    finally:
        readiness.cancel()
        instance.should_exit = True
        await task


if __name__ == '__main__':
    sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
    observed = (asyncio.run(asyncio.wait_for(server(), timeout=30))
                if sys.argv[2] == 'server' else formatter())
    Path(sys.argv[3]).write_text(json.dumps(observed), encoding='utf-8')
