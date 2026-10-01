from typing import Literal

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import observability as log
from .middleware import RequestContextMiddleware
from .provider import ProviderTimeout
from .service import create_order


class Order(BaseModel):
    order_id: str = Field(min_length=1)
    amount_cents: int = Field(gt=0)
    provider_mode: Literal['success', 'timeout'] = 'success'
    payment_token: str = 'TEST_SECRET_DEFAULT'


log.configure()
app = FastAPI(title='Logging skill demo: orders')
app.add_middleware(RequestContextMiddleware)


@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.post('/orders', status_code=201)
async def orders(order: Order):
    try:
        return await create_order(order)
    except ProviderTimeout:
        log.exception('order.failed', order_id=order.order_id, retryable=True)
        return JSONResponse(status_code=503, content={'detail': 'provider unavailable'})
