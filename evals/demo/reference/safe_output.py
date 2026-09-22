import re


def sanitize(value):
    """Demo redaction after exception rendering; not a general secret detector."""
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return re.sub(r'TEST_SECRET_[A-Z0-9_]+', '[REDACTED]', value)
    return value
