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
    try:
        if amount_cents < 0:
            raise PaymentGatewayError("negative amount")

        logger.info(f"invoice_{invoice_id}_processed for customer {customer_id} request={request_id} attempt={attempt}")
    except PaymentGatewayError as exc:
        logger.error(f"invoice processing failed for {invoice_id}: {exc}")
        raise
