import logging


logger = logging.getLogger(__name__)


def process_invoice(
    invoice_id: str,
    customer_id: str,
    request_id: str,
    attempt: int,
    payment_payload: dict,
) -> None:
    print("starting invoice processing", invoice_id, customer_id, request_id)
    logger.info(
        f"processing invoice {invoice_id} for customer {customer_id} attempt={attempt}"
    )

    try:
        logger.info(
            f"invoice_{invoice_id}_processed",
            extra={
                "payload": payment_payload,
                "request": request_id,
                "authorization_header": "Bearer secret-token",
            },
        )
    except Exception as exc:
        logger.error(f"invoice processing failed for {invoice_id}: {exc}")
        return
