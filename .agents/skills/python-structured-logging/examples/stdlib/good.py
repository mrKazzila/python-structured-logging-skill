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
    shared_context = {
        "request_id": request_id,
        "invoice_id": invoice_id,
        "customer_id": customer_id,
        "attempt": attempt,
    }
    safe_payment = {
        "amount_cents": amount_cents,
        "card_last4": "4242",
    }

    try:
        if amount_cents < 0:
            raise PaymentGatewayError("negative amount")

        logger.info(
            "invoice_processed",
            extra={
                **shared_context,
                "status": "success",
                "payment": safe_payment,
            },
        )
    except PaymentGatewayError:
        logger.exception(
            "invoice_processing_failed",
            extra={
                **shared_context,
                "retryable": True,
                "payment": safe_payment,
            },
        )
        raise
