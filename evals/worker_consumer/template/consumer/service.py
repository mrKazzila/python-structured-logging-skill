from . import observability as log


async def process(message, dependency):
    log.info(f'processing_{message.message_id}', payload=message.payload)
    try:
        result = await dependency.execute(message)
    except Exception:
        log.exception('service.failed')
        raise
    log.info('service.done')
    return result
