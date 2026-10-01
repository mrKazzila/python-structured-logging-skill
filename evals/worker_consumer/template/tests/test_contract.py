import asyncio
import unittest
from consumer.broker import Broker, Message
from consumer.dependency import Dependency
from consumer.worker import Consumer
from consumer.runtime import run


class Contracts(unittest.IsolatedAsyncioTestCase):
    async def test_dispositions(self):
        broker, dep = Broker(), Dependency()
        consumer = Consumer(broker, dep)
        messages = [Message(mode, 'c-'+mode, {'mode': mode, 'amount_cents': 100}, attempt)
                    for mode, attempt in [('success', 1), ('retry', 1), ('exhausted', 3),
                                          ('poison', 1), ('unexpected', 1)]]
        results = await run(consumer, messages)
        self.assertEqual(results[:4], [{'message_id': 'success', 'amount_cents': 100},
                                     'retry', 'dead_letter', 'dead_letter'])
        self.assertIsInstance(results[4], RuntimeError)
        self.assertEqual(sorted(broker.dispositions), sorted([
            ('success', 'ack', 1), ('retry', 'retry', 1), ('exhausted', 'dead_letter', 3),
            ('poison', 'dead_letter', 1), ('unexpected', 'retry', 1)]))
        self.assertEqual(len(dep.calls), 5)

    async def test_cancel_and_redelivery(self):
        broker, dep = Broker(), Dependency()
        consumer = Consumer(broker, dep)
        task = asyncio.create_task(consumer.handle(Message('cancel', 'c', {'mode':'cancel','amount_cents':1})))
        await dep.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(broker.dispositions, [])
        result = await consumer.handle(Message('retry', 'c', {'mode':'retry','amount_cents':1}, 2))
        self.assertEqual(result, {'message_id':'retry','amount_cents':1})
        await consumer.drain()
        self.assertEqual(broker.dispositions, [('retry','ack',2)])
