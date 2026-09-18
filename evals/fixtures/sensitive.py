import logging

logger = logging.getLogger(__name__)


def process_request(payload):
    try:
        raise ValueError('upstream rejected token=TEST_SECRET_DO_NOT_USE')
    except ValueError:
        logger.exception('request_failed', extra={'payload': payload})
        raise
