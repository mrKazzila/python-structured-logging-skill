"""Deterministic calibration repair, not an experiment candidate."""
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent


def repair(project):
    shutil.copyfile(HERE/'reference/observability.py',project/'consumer/observability.py')
    (project/'consumer/service.py').write_text('async def process(message, dependency):\n    return await dependency.execute(message)\n')
    p=project/'consumer/worker.py'; s=p.read_text()
    s=s.replace("            log.info('message.received', payload=message.payload, attempt=message.attempt)\n",'')
    s=s.replace("log.exception('message.retry', attempt=message.attempt, retryable=True)","log.warning('message.retry', attempt=message.attempt, retryable=True, outcome='retry')")
    s=s.replace("attempt=message.attempt, retryable=False)","attempt=message.attempt, retryable=False, outcome='dead_letter')")
    s=s.replace("                log.exception('message.cancelled')\n",'')
    s=s.replace("                log.exception('message.failed')\n",'')
    s=s.replace("outcome='ack')","outcome='ack', attempt=message.attempt)")
    s=s.replace("                log.exception('audit.failed', message_id=message.message_id)","                with log.scope(message_id=message.message_id, correlation_id=message.correlation_id):\n                    log.exception('audit.failed', attempt=message.attempt, outcome='failed')")
    p.write_text(s)
    p=project/'consumer/runtime.py'; s=p.read_text()
    s=s.replace("            runtime_log.error('consumer failed: %s', result,\n                              exc_info=(type(result), result, result.__traceback__))", "            with log.scope(message_id=message.message_id, correlation_id=message.correlation_id):\n                log.warning('message.failed', attempt=message.attempt, outcome='failed', error_type=type(result).__name__)")
    p.write_text(s)
