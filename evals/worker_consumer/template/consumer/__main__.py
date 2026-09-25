import asyncio
import logging
from . import observability as log
from .broker import Broker, Message
from .dependency import Dependency
from .worker import Consumer
from .runtime import run

logging.basicConfig(level=logging.INFO)
log.configure()
asyncio.run(run(Consumer(Broker(), Dependency()), [
    Message('demo', 'corr-demo', {'amount_cents':100,'mode':'success'})]))
