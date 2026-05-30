import structlog


logger = structlog.get_logger(__name__)


def process_invoice(invoice_id: str, customer_id: str, attempt: int, duration_ms: int) -> None:
    log = logger.bind(
        invoice_id=invoice_id,
        customer_id=customer_id,
        attempt=attempt,
    )
    log.info("invoice_processing_started")

    try:
        log.info(
            "invoice_processed",
            status="success",
            duration_ms=duration_ms,
        )
    except Exception:
        log.exception(
            "invoice_processing_failed",
            retryable=True,
        )
        raise
