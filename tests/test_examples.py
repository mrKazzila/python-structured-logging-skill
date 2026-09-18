"""Exercise emitted records and business behavior, not source spelling."""

import importlib.util
import inspect
import io
import json
import logging
import unittest
from pathlib import Path

import structlog

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'plugins/python-structured-logging/skills/python-structured-logging/examples'


def load(stack, quality):
    name = f'example_{stack}_{quality}'
    spec = importlib.util.spec_from_file_location(name, EXAMPLES / stack / f'{quality}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JsonFormatter(logging.Formatter):
    """Test output pipeline; application modules do not install handlers."""

    def format(self, record):
        payload = {'event': record.getMessage()}
        for key in ('request_id', 'invoice_id', 'customer_id', 'attempt', 'amount_cents', 'retryable'):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload)


class ExampleTests(unittest.TestCase):
    def test_pairs_preserve_signatures_and_business_behavior(self):
        for stack in ('stdlib', 'structlog'):
            with self.subTest(stack=stack):
                good, bad = load(stack, 'good'), load(stack, 'bad')
                self.assertEqual(inspect.signature(good.process_invoice), inspect.signature(bad.process_invoice))
                for module in (good, bad):
                    # Keep intentionally bad log output out of the test runner.
                    with structlog.testing.capture_logs():
                        logger = logging.getLogger(module.__name__)
                        old_disabled = logger.disabled
                        logger.disabled = True
                        try:
                            self.assertIsNone(module.process_invoice('i', 'c', 'r', 1, 100))
                            with self.assertRaisesRegex(module.PaymentGatewayError, '^negative amount$'):
                                module.process_invoice('i', 'c', 'r', 1, -1)
                        finally:
                            logger.disabled = old_disabled

    def test_stdlib_rendered_success_failure_and_context(self):
        module = load('stdlib', 'good')
        logger = module.logger
        previous = logger.handlers[:], logger.level, logger.propagate
        output = io.StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(JsonFormatter())
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False
        try:
            module.process_invoice('i1', 'c1', 'r1', 1, 100)
            with self.assertRaises(module.PaymentGatewayError):
                module.process_invoice('i2', 'c2', 'r2', 2, -1)
        finally:
            logger.handlers, logger.level, logger.propagate = previous
        self.check_records([json.loads(line) for line in output.getvalue().splitlines()])

    def test_structlog_rendered_success_failure_and_context(self):
        previous = structlog.get_config().copy()
        configured = structlog.is_configured()
        output = io.StringIO()
        try:
            structlog.configure(
                processors=[structlog.processors.format_exc_info, structlog.processors.JSONRenderer()],
                logger_factory=structlog.PrintLoggerFactory(file=output),
                cache_logger_on_first_use=False,
            )
            module = load('structlog', 'good')
            module.process_invoice('i1', 'c1', 'r1', 1, 100)
            with self.assertRaises(module.PaymentGatewayError):
                module.process_invoice('i2', 'c2', 'r2', 2, -1)
        finally:
            if configured:
                structlog.configure(**previous)
            else:
                structlog.reset_defaults()
        self.check_records([json.loads(line) for line in output.getvalue().splitlines()])

    def check_records(self, records):
        self.assertEqual(len(records), 2)
        success, failure = records
        self.assertEqual(success['event'], 'invoice_processed')
        self.assertEqual(success['request_id'], 'r1')
        self.assertEqual(success['invoice_id'], 'i1')
        self.assertEqual(success['amount_cents'], 100)
        self.assertNotIn('exception', success)
        self.assertEqual(failure['event'], 'invoice_processing_failed')
        self.assertEqual(failure['request_id'], 'r2')
        self.assertEqual(failure['invoice_id'], 'i2')
        self.assertIs(failure['retryable'], False)
        self.assertIn('Traceback', failure['exception'])
        self.assertIn('PaymentGatewayError: negative amount', failure['exception'])
        self.assertNotIn('payment', failure)
