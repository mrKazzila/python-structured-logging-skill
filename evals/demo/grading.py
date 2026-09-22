"""Grade observable outcomes without prescribing a particular repair."""

import json


def grade(observations, stack):
    criteria = []

    def result(name, passed, evidence):
        criteria.append({'id': name, 'passed': bool(passed), 'evidence': evidence})

    records, malformed = [], []
    for stream in ('stdout', 'stderr'):
        for line in observations[stream].splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict) or not isinstance(record.get('event'), str):
                    raise ValueError('expected JSON object with string event')
                records.append(record)
            except (ValueError, TypeError):
                malformed.append(line)
    result('json_output', bool(records) and not malformed,
           {'records': len(records), 'malformed_lines': malformed})

    responses = observations['responses']
    labels = {'health', 'success', 'failure', 'invalid', 'parallel_success', 'parallel_failure'}
    business_errors = []
    for response in responses:
        label = response['label']
        expected_status = 200 if label == 'health' else 422 if label == 'invalid' else 503 if response['mode'] == 'timeout' else 201
        expected_body = ({'status': 'ok'} if label == 'health' else
                         {'detail': 'provider unavailable'} if expected_status == 503 else
                         {'order_id': response['order_id'], 'status': 'created'})
        if response['status'] != expected_status or (expected_status != 422 and response['body'] != expected_body):
            business_errors.append(response)
        if not response['request_id'] or (response['expected_request_id'] and response['request_id'] != response['expected_request_id']):
            business_errors.append(response)
    result('http_contract', len(responses) == len(labels) and {r['label'] for r in responses} == labels and not business_errors,
           business_errors or responses)
    provider = observations['provider']
    result('provider_behavior', provider == {
        'success': {'order_id': 'direct', 'status': 'created'},
        'failure': {'type': 'ProviderTimeout',
                    'message': 'provider timed out; credential=TEST_SECRET_PAYMENT'},
    }, provider)

    successful = [r for r in responses if r['label'] in ('success', 'parallel_success')]
    failed = [r for r in responses if r['label'] in ('failure', 'parallel_failure')]
    created = [r for r in records if r['event'] == 'order.created']
    failures = [r for r in records if r['event'] == 'order.failed']
    completed = [r for r in records if r['event'] == 'request.completed']
    result('event_contracts', len(created) == 2 and len(failures) >= 2 and len(completed) == 6,
           {'order.created': len(created), 'order.failed': len(failures), 'request.completed': len(completed)})
    variable_names = [r['event'] for r in records if any(
        value and value in r['event'] for response in responses
        for value in (response['order_id'], response['request_id']))]
    result('stable_events', not variable_names, {'variable_events': variable_names})

    field_errors = []
    for response in successful:
        matches = [r for r in created if r.get('order_id') == response['order_id']]
        if len(matches) != 1 or matches[0].get('amount_cents') != response['amount_cents']:
            field_errors.append(response['label'])
    for response in failed:
        if not any(r.get('order_id') == response['order_id'] and r.get('retryable') is True for r in failures):
            field_errors.append(response['label'])
    result('structured_fields', not field_errors, {'missing_or_wrong_fields': field_errors})

    # Count all ERROR/CRITICAL records, not only the contracted event name.
    error_records = [r for r in records if str(r.get('level', r.get('log_level', r.get('levelname', '')))).lower() in ('error', 'critical')]
    ownership_errors = []
    for response in failed:
        matches = [r for r in error_records if r.get('order_id') == response['order_id']]
        if len(matches) != 1 or matches[0]['event'] != 'order.failed':
            ownership_errors.append(response['label'])
        elif 'ProviderTimeout' not in json.dumps(matches[0]) or 'Traceback' not in json.dumps(matches[0]):
            ownership_errors.append(response['label'])
    result('single_failure_traceback', len(error_records) == 2 and not ownership_errors,
           {'error_records': len(error_records), 'invalid_failures': ownership_errors})

    raw = observations['stdout'] + observations['stderr']
    markers = [marker for marker in ('TEST_SECRET_HEADER', 'TEST_SECRET_PAYMENT', 'TEST_SECRET_DEFAULT') if marker in raw]
    result('no_secrets', not markers, {'leaked_markers': markers})

    correlation_errors = []
    for response in responses:
        matches = [r for r in completed if r.get('request_id') == response['request_id']]
        if len(matches) != 1 or matches[0].get('status_code') != response['status']:
            correlation_errors.append(response['label'])
        if response in successful + failed:
            event = 'order.created' if response in successful else 'order.failed'
            matches = [r for r in records if r['event'] == event and r.get('order_id') == response['order_id']]
            if not matches or any(r.get('request_id') != response['request_id'] for r in matches):
                correlation_errors.append(response['label'])
    result('request_isolation', not correlation_errors, {'wrong_request_context': correlation_errors})
    probes = [r for r in records if r['event'] == 'demo.probe']
    result('context_cleanup', len(probes) == 6 and {r.get('probe_id') for r in probes} == labels and
           all(r.get('request_id') is None for r in probes), {'probes': probes})
    usage = observations['backend_calls']
    preserved = usage[stack] > 0 and (stack != 'stdlib' or usage['structlog'] == 0)
    result('original_stack', preserved, usage)
    return criteria
