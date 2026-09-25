import logging

logger = logging.getLogger(__name__)


class PaymentGatewayError(RuntimeError):
    pass


def process_invoice(
    invoice_id: str,
    customer_id: str,
    request_id: str,
    attempt: int,
    amount_cents: int,
) -> None:
    # This operation owns the failure record; callers propagate without logging.
    context = {
        "request_id": request_id,
        "invoice_id": invoice_id,
        "customer_id": customer_id,
        "attempt": attempt,
    }
    try:
        if amount_cents < 0:
            raise PaymentGatewayError("negative amount")

        logger.info("invoice_processed", extra={**context, "amount_cents": amount_cents})
    except PaymentGatewayError:
        logger.exception("invoice_processing_failed", extra={**context, "retryable": False})
        raise
