import structlog

logger = structlog.get_logger(__name__)


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
    log = logger.bind(**context)
    try:
        if amount_cents < 0:
            raise PaymentGatewayError("negative amount")

        log.info("invoice_processed", amount_cents=amount_cents)
    except PaymentGatewayError:
        log.exception("invoice_processing_failed", retryable=False)
        raise
