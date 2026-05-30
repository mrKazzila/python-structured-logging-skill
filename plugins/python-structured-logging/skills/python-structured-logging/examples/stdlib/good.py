import logging


logger = logging.getLogger(__name__)


def process_invoice(invoice_id: str, customer_id: str, attempt: int, duration_ms: int) -> None:
    logger.info(
        "invoice_processing_started",
        extra={
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "attempt": attempt,
        },
    )

    try:
        logger.info(
            "invoice_processed",
            extra={
                "invoice_id": invoice_id,
                "customer_id": customer_id,
                "attempt": attempt,
                "status": "success",
                "duration_ms": duration_ms,
            },
        )
    except Exception:
        logger.exception(
            "invoice_processing_failed",
            extra={
                "invoice_id": invoice_id,
                "customer_id": customer_id,
                "attempt": attempt,
                "retryable": True,
            },
        )
        raise
