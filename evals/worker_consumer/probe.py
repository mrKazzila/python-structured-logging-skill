"""Run in an isolated process; metadata never shares the logging output streams."""
import asyncio
import copy
import json
import logging
import os
import tempfile
from contextlib import contextmanager
import sys
from pathlib import Path

SECRETS = ['SYNTHETIC_DEPENDENCY_SECRET', 'SYNTHETIC_BARE_SECRET',
           'SYNTHETIC_PAYLOAD_SECRET', 'SYNTHETIC_AUDIT_SECRET', 'SYNTHETIC_TOKEN_SECRET']


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


async def workload():
    from consumer import observability as log
    from consumer.broker import Broker, Message
    from consumer.dependency import Dependency
    from consumer.worker import Consumer
    from consumer.runtime import run

    class ObservedDependency(Dependency):
        def __init__(self):
            super().__init__()
            self.audit_started = []
            self.audit_completed = []

        async def audit(self, message):
            self.audit_started.append(message.message_id)
            try:
                return await super().audit(message)
            finally:
                self.audit_completed.append(message.message_id)

        async def execute(self, message):
            with log.scope(operation='nested'):
                await asyncio.sleep(0)
                log.info('probe.nested', probe_message=message.message_id)
            log.info('probe.parent', probe_message=message.message_id)
            return await super().execute(message)

    def msg(name, mode, attempt=1, audit=False):
        return Message(name, 'corr-'+name, {'mode':mode, 'amount_cents':123,
                       'body':'SYNTHETIC_PAYLOAD_SECRET', 'payment_token':'SYNTHETIC_TOKEN_SECRET',
                       'audit_fail':audit}, attempt)

    messages = [msg('ok','success'), msg('retry','retry'), msg('redelivered','retry',2),
                msg('poison','poison'), msg('exhausted','exhausted',3),
                msg('unexpected','unexpected'), msg('audit','success',audit=True)]
    payload_ids = [id(m.payload) for m in messages]
    payloads = copy.deepcopy([m.payload for m in messages])
    broker, dep = Broker(), ObservedDependency()
    consumer = Consumer(broker, dep)
    original_handle = consumer.handle

    async def observed_handle(message):
        try:
            return await original_handle(message)
        finally:
            log.info('probe.cleanup', probe_message=message.message_id)
    consumer.handle = observed_handle
    results = await run(consumer, messages)
    # Verify direct unexpected propagation separately, without runtime ack/retry.
    direct_broker, direct_dep = Broker(), Dependency()
    direct = Consumer(direct_broker, direct_dep)
    try:
        await direct.handle(msg('direct','unexpected'))
    except Exception as error:
        direct_error = {'type':type(error).__name__, 'message':str(error)}
    else:
        direct_error = None
    log.info('probe.cleanup', probe_message='direct')
    cancel_broker, cancel_dep = Broker(), Dependency()
    cancel_consumer = Consumer(cancel_broker, cancel_dep)
    async def cancel_job():
        try:
            await cancel_consumer.handle(msg('cancel','cancel'))
        finally:
            log.info('probe.cleanup', probe_message='cancel')
    task = asyncio.create_task(cancel_job())
    await cancel_dep.started.wait()
    task.cancel()
    cancelled = False
    try:
        await task
    except asyncio.CancelledError:
        cancelled = True
    with log.scope(message_id='outer', correlation_id='corr-outer'):
        with log.scope(message_id='inner', correlation_id='corr-inner'):
            log.info('probe.scope_inner')
        log.info('probe.scope_outer')
    log.info('probe.scope_clear')
    direct_contracts = []
    for mode in ('retry','poison','unexpected'):
        try:
            await Dependency().execute(msg('dependency',mode))
        except Exception as error:
            direct_contracts.append({'type':type(error).__name__,'message':str(error)})
    return {'results':[{'type':type(r).__name__,'message':str(r)} if isinstance(r,BaseException) else r for r in results],
            'dispositions':broker.dispositions, 'calls':dep.calls,
            'payloads_preserved':payloads == [m.payload for m in messages] and payload_ids == [id(m.payload) for m in messages],
            'audit_started':dep.audit_started, 'audit_completed':dep.audit_completed,
            'direct_error':direct_error, 'direct_dispositions':direct_broker.dispositions,
            'cancelled':cancelled, 'cancel_dispositions':cancel_broker.dispositions,
            'background_remaining':len(consumer.background), 'dependency_contracts':direct_contracts}


def malformed(case):
    from consumer import observability as log
    class Unknown:
        def __str__(self):
            raise ValueError('SYNTHETIC_BARE_SECRET')
        __repr__ = __str__
    cycle = {}; cycle['self'] = cycle
    values = {'nonfinite':[float('nan'),float('inf'),float('-inf')],
              'object':object(), 'key':{Unknown():'safe'}, 'cycle':cycle}
    raised = None
    with capture_streams() as emission:
        try:
            raise RuntimeError('SYNTHETIC_BARE_SECRET')
        except RuntimeError:
            try:
                log.exception('probe.malformed', value=values[case])  # WORKER_SOURCE_SENTINEL
            except Exception as error:
                raised = type(error).__name__
    recovery_raised = None
    with capture_streams() as recovery:
        try:
            log.info('probe.recovery')
        except Exception as error:
            recovery_raised = type(error).__name__
    return {'raised':raised, 'recovery_raised':recovery_raised,
            'emission':emission, 'recovery':recovery}



if __name__ == '__main__':
    sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
    logging.basicConfig(level=logging.INFO)  # Adapter bootstrap, before facade configuration.
    from consumer import observability as log
    log.configure()
    logging.raiseExceptions = True
    result = asyncio.run(asyncio.wait_for(workload(), 15)) if sys.argv[2]=='workload' else malformed(sys.argv[2])
    Path(sys.argv[3]).write_text(json.dumps(result))
