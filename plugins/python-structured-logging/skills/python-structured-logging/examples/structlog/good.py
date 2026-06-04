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
    log = logger.bind(
        request_id=request_id,
        invoice_id=invoice_id,
        customer_id=customer_id,
        attempt=attempt,
    )
    safe_payment = {
        "amount_cents": amount_cents,
        "card_last4": "4242",
    }

    try:
        if amount_cents < 0:
            raise PaymentGatewayError("negative amount")

        log.info(
            "invoice_processed",
            status="success",
            payment=safe_payment,
        )
    except PaymentGatewayError:
        log.exception(
            "invoice_processing_failed",
            retryable=True,
            payment=safe_payment,
        )
        raise
