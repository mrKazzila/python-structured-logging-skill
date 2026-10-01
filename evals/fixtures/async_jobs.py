import asyncio

import structlog

structlog.configure(processors=[
    structlog.contextvars.merge_contextvars,
    structlog.processors.JSONRenderer(),
])
logger = structlog.get_logger()


async def run_job(job_id):
    structlog.contextvars.bind_contextvars(job_id=job_id)
    await asyncio.sleep(0)
    logger.info('job_processed')


async def main():
    await asyncio.gather(run_job('one'), run_job('two'))
    await run_job('three')
    logger.info('worker_idle')


if __name__ == '__main__':
    asyncio.run(main())
