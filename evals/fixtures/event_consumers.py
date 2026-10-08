"""Local consumers of invoice events emitted by service.py."""


def failed_invoices(events):
    return [event['invoice_id'] for event in events
            if event['event'] == 'invoice.charge.failed']


def completed_total(events):
    return sum(event['amount_cents'] for event in events
               if event['event'] == 'invoice.charge.completed')
