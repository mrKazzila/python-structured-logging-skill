import unittest

from httpx import ASGITransport, AsyncClient

from app.main import app


class ContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_contract(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://demo') as client:
            response = await client.get('/health')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {'status': 'ok'})
            self.assertTrue(response.headers['x-request-id'])
            response = await client.post('/orders', json={'order_id': 'one', 'amount_cents': 100}, headers={'X-Request-ID': 'request-one'})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json(), {'order_id': 'one', 'status': 'created'})
            self.assertEqual(response.headers['x-request-id'], 'request-one')
            response = await client.post('/orders', json={'order_id': 'two', 'amount_cents': 100, 'provider_mode': 'timeout'})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json(), {'detail': 'provider unavailable'})
            response = await client.post('/orders', json={'order_id': 'three', 'amount_cents': -1})
            self.assertEqual(response.status_code, 422)
