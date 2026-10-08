import asyncio

import structlog

structlog.configure(processors=[
    structlog.contextvars.merge_contextvars,
    structlog.processors.JSONRenderer(),
])
logger = structlog.get_logger()


async def fetch_invoice():
    await asyncio.sleep(0)
    structlog.get_logger().info('invoice_fetched')
    return 100


async def handle_request(request_id):
    log = logger.bind(request_id=request_id)
    result = await fetch_invoice()
    log.info('request_completed')
    return result


async def main():
    await asyncio.gather(handle_request('one'), handle_request('two'))
    await fetch_invoice()


if __name__ == '__main__':
    asyncio.run(main())
