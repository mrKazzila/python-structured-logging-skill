import structlog


logger = structlog.get_logger(__name__)


def process_invoice(
    invoice_id: str,
    customer_id: str,
    request_id: str,
    attempt: int,
    payment_payload: dict,
) -> None:
    try:
        logger.info(
            f"starting invoice processing for invoice={invoice_id}, customer={customer_id}, request={request_id}"
        )
        logger.info(
            f"invoice_{invoice_id}_processed",
            payload=payment_payload,
            attempt=attempt,
            authorization_header="Bearer secret-token",
        )
    except Exception as exc:
        logger.error(f"invoice processing failed for {invoice_id}: {exc}")
        raise
