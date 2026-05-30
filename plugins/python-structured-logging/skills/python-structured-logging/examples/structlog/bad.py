import structlog


logger = structlog.get_logger(__name__)


def process_invoice(invoice_id: str, customer_id: str, attempt: int, duration_ms: int) -> None:
    try:
        logger.info(
            f"Starting invoice processing for invoice={invoice_id}, customer={customer_id}, attempt={attempt}"
        )
        logger.info(
            f"Invoice {invoice_id} for customer {customer_id} processed in {duration_ms} ms"
        )
    except Exception as exc:
        logger.error(f"Invoice processing failed for {invoice_id}: {exc}")
        raise
