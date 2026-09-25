import contextlib
import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import demo

STACKS = [os.environ['DEMO_TEST_STACK']] if os.environ.get('DEMO_TEST_STACK') else ['stdlib', 'structlog']


def repair(project, stack):
    reference = demo.DEMO / 'reference'
    shutil.copyfile(reference / f'{stack}.py', project / 'app/observability.py')
    for filename in ('service.py', 'safe_output.py', 'runtime_boundary.py'):
        shutil.copyfile(reference / filename, project / 'app' / filename)
    middleware = project / 'app/middleware.py'
    middleware.write_text(middleware.read_text().replace(
        "log.info('request.received', authorization=headers.get(b'authorization', b'').decode())",
        "log.info('request.received')",
    ))
    main = project / 'app/main.py'
    main.write_text(main.read_text() +
                    '\nfrom .runtime_boundary import RuntimeBoundary\napp = RuntimeBoundary(app)\n')


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def project(self, stack, fixed=False):
        project = self.root / stack
        with contextlib.redirect_stdout(io.StringIO()):
            demo.create(stack, project)
        # Tests reuse the pinned test environment, never install from the checker.
        (project / '.venv').symlink_to(Path(sys.prefix), target_is_directory=True)
        if fixed:
            repair(project, stack)
        return project

    def test_originals_have_working_api_and_reproducible_logging_defects(self):
        expected_failures = {'stable_events', 'structured_fields', 'single_failure_traceback',
                             'no_secrets', 'request_isolation', 'context_cleanup',
                             'whole_process_output',
                             'formatter_fallback_safety', 'unexpected_500_correlation'}
        for stack in STACKS:
            with self.subTest(stack=stack):
                project = self.project(stack)
                result = demo.check(project)
                criteria = {c['id']: c['passed'] for c in result['criteria']}
                self.assertTrue(criteria['http_contract'])
                self.assertTrue(criteria['original_stack'])
                self.assertTrue(criteria['json_output'])
                self.assertTrue(criteria['event_contracts'])
                self.assertEqual({name for name, passed in criteria.items() if not passed}, expected_failures)
                business = subprocess.run(
                    [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                    cwd=project, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(business.returncode, 0, business.stderr)

    def test_reference_repairs_pass_every_criterion(self):
        for stack in STACKS:
            with self.subTest(stack=stack):
                report = demo.check(self.project(stack, fixed=True))
                self.assertTrue(report['passed'], report['criteria'])
                self.assertTrue(report['versions']['fastapi'])

    def reviewed_worker(self):
        project = self.project('stdlib')
        for source in (demo.DEMO / 'regressions/reviewed_worker').glob('*.py'):
            shutil.copyfile(source, project / 'app' / source.name)
        return project

    def reviewed_report(self):
        report = demo.check(self.reviewed_worker())
        self.assertEqual(len(report['criteria']), 15)
        self.assertTrue(all(c['passed'] for c in report['criteria'][:11]))
        self.assertFalse(report['passed'])
        return report

    def test_reviewed_worker_whole_process_output(self):
        report = self.reviewed_report()
        check = next(c for c in report['criteria'] if c['id'] == 'whole_process_output')
        self.assertFalse(check['passed'])
        self.assertEqual(len(check['evidence']['leaked_markers']), 2)

    def test_reviewed_worker_duplicate_failure_ownership(self):
        report = self.reviewed_report()
        check = next(c for c in report['criteria'] if c['id'] == 'unexpected_failure_ownership')
        self.assertFalse(check['passed'])
        self.assertEqual(check['evidence'], {'error_records': 1, 'raw_server_errors': 1})

    def test_reviewed_worker_formatter_fallback(self):
        report = self.reviewed_report()
        check = next(c for c in report['criteria'] if c['id'] == 'formatter_fallback_safety')
        self.assertFalse(check['passed'])
        self.assertIn('--- Logging error ---', check['evidence']['unsafe_markers'])
        self.assertIn('FORMATTER_SOURCE_SENTINEL', check['evidence']['unsafe_markers'])
        self.assertTrue(any('TEST_SECRET_FORMATTER_' in s for s in check['evidence']['unsafe_markers']))

    def test_reviewed_worker_unexpected_500_correlation(self):
        report = self.reviewed_report()
        check = next(c for c in report['criteria'] if c['id'] == 'unexpected_500_correlation')
        self.assertFalse(check['passed'])
        self.assertEqual(check['evidence']['status'], 500)
        self.assertIsNone(check['evidence']['response_request_id'])
        self.assertIn('request.completed', check['evidence']['correlated_events'])

    def test_minimal_reviewed_worker_repairs_pass(self):
        project = self.reviewed_worker()
        for filename in ('safe_output.py', 'runtime_boundary.py'):
            shutil.copyfile(demo.DEMO / 'reference' / filename, project / 'app' / filename)
        backend = project / 'app/observability.py'
        backend.write_text(backend.read_text().replace(
            'import json', 'import json\nimport math\nfrom .safe_output import configure_server',
        ).replace('def _safe(value):',
                  'def _safe(value):\n    if isinstance(value, float) and not math.isfinite(value):\n        return None'
        ).replace('def configure():', 'def configure():\n    configure_server()'))
        middleware = project / 'app/middleware.py'
        middleware.write_text(middleware.read_text().replace(
            "log.exception('request.failed', status_code=status)", 'pass  # Outer boundary owns failure'))
        main = project / 'app/main.py'
        main.write_text(main.read_text() +
                        '\nfrom .runtime_boundary import RuntimeBoundary\napp = RuntimeBoundary(app)\n')
        report = demo.check(project)
        self.assertTrue(report['passed'], report['criteria'])

    def test_independent_runtime_source_regressions(self):
        mutations = {
            'whole_process_output': ('observability.py', '    configure_server()', '    pass'),
            'unexpected_failure_ownership': (
                'runtime_boundary.py', "log.exception('request.failed', request_id=request_id)",
                "log.exception('request.failed', request_id=request_id)\n"
                "            log.exception('duplicate.failure', request_id=request_id)"),
            'formatter_fallback_safety': ('safe_output.py',
                'if isinstance(value, float) and not math.isfinite(value):',
                'if False:'),
            'unexpected_500_correlation': ('runtime_boundary.py',
                "message = {**message, 'headers': [*headers, (b'x-request-id', request_id.encode())]}",
                'message = message'),
        }
        for stack in STACKS:
            for criterion, (filename, before, after) in mutations.items():
                with self.subTest(stack=stack, criterion=criterion):
                    with tempfile.TemporaryDirectory(dir=self.root) as temporary:
                        project = Path(temporary) / 'project'
                        with contextlib.redirect_stdout(io.StringIO()):
                            demo.create(stack, project)
                        (project / '.venv').symlink_to(Path(sys.prefix), target_is_directory=True)
                        repair(project, stack)
                        target = project / 'app' / filename
                        self.assertIn(before, target.read_text())
                        target.write_text(target.read_text().replace(before, after))
                        report = demo.check(project)
                        self.assertEqual([c['id'] for c in report['criteria'] if not c['passed']],
                                         [criterion], report['criteria'])

    def test_each_regression_is_detected_in_rendered_observations(self):
        spec = importlib.util.spec_from_file_location('grading_test', demo.DEMO / 'grading.py')
        grading = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(grading)
        for stack in STACKS:
            with self.subTest(stack=stack):
                original = demo.check(self.project(stack, fixed=True))['observations']
                records = [json.loads(line) for line in original['stderr'].splitlines()]

                def assert_fails(criterion, mutate):
                    observed = copy.deepcopy(original)
                    changed = copy.deepcopy(records)
                    mutate(changed, observed)
                    observed['stderr'] = '\n'.join(json.dumps(r) for r in changed)
                    results = {c['id']: c['passed'] for c in grading.grade(observed, stack)}
                    self.assertFalse(results[criterion], criterion)

                assert_fails('structured_fields', lambda rows, obs: [r.pop('amount_cents', None) for r in rows])
                assert_fails('stable_events', lambda rows, obs: rows.append({'event': 'order_order-alpha_accepted'}))
                assert_fails('single_failure_traceback', lambda rows, obs: rows.append(copy.deepcopy(next(r for r in rows if r['event'] == 'order.failed'))))
                assert_fails('single_failure_traceback', lambda rows, obs: [r.pop('exception', None) for r in rows])
                assert_fails('no_secrets', lambda rows, obs: next(r for r in rows if r['event'] == 'order.failed').update(exception='TEST_SECRET_PAYMENT'))
                assert_fails('no_secrets', lambda rows, obs: obs.update(stdout='TEST_SECRET_HEADER'))
                assert_fails('request_isolation', lambda rows, obs: next(r for r in rows if r['event'] == 'order.created').update(request_id='wrong'))
                assert_fails('context_cleanup', lambda rows, obs: next(r for r in rows if r['event'] == 'demo.probe').update(request_id='leaked'))
                assert_fails('event_contracts', lambda rows, obs: [r.update(event='renamed') for r in rows if r['event'] == 'order.created'])
                assert_fails('http_contract', lambda rows, obs: obs['responses'][0].update(status=500))
                assert_fails('provider_behavior', lambda rows, obs: obs['provider']['failure'].update(message='redacted'))
                assert_fails('original_stack', lambda rows, obs: obs.update(backend_calls={'stdlib': 0, 'structlog': 0}))
                assert_fails('json_output', lambda rows, obs: obs.update(stdout='plain prose'))

    def test_source_regressions_fail_after_reference_repair(self):
        for stack in STACKS:
            with self.subTest(stack=stack):
                project = self.project(stack, fixed=True)
                backend = project / 'app/observability.py'
                backend.write_text(backend.read_text().replace('_context.reset(token)', 'pass'))
                result = demo.check(project)
                self.assertFalse(next(c['passed'] for c in result['criteria'] if c['id'] == 'context_cleanup'))

    def test_create_excludes_graders_and_refuses_existing_destination(self):
        project = self.project(STACKS[0])
        self.assertTrue((project / 'PROMPT.md').is_file())
        self.assertTrue((project / 'requirements.txt').is_file())
        self.assertFalse((project / 'runner.py').exists())
        self.assertFalse((project / 'reference').exists())
        before = (project / 'app/main.py').read_bytes()
        with self.assertRaises(ValueError):
            demo.create(STACKS[0], project)
        self.assertEqual((project / 'app/main.py').read_bytes(), before)

    def test_report_exit_codes_and_no_overwrite(self):
        project = self.project(STACKS[0])
        args = ['check', '--project', str(project), '--report', str(self.root / 'before.json')]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(demo.main(args), 1)
            content = (self.root / 'before.json').read_bytes()
            self.assertEqual(demo.main(args), 2)
            self.assertEqual((self.root / 'before.json').read_bytes(), content)
            repair(project, STACKS[0])
            args[-1] = str(self.root / 'after.json')
            self.assertEqual(demo.main(args), 0)
        self.assertTrue(json.loads((self.root / 'after.json').read_text())['passed'])

    def test_missing_environment_and_probe_failure_are_setup_errors(self):
        project = self.project(STACKS[0])
        (project / '.venv').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing virtual environment'):
            demo.check(project)
        (project / '.venv').symlink_to(Path(sys.prefix), target_is_directory=True)
        (project / 'app/main.py').write_text('raise RuntimeError("broken startup")\n')
        with self.assertRaisesRegex(ValueError, 'broken startup'):
            demo.check(project)
        report = self.root / 'error.json'
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(demo.main(['check', '--project', str(project), '--report', str(report)]), 2)
        self.assertIsNone(json.loads(report.read_text())['passed'])

    def test_timeout_is_a_setup_error(self):
        project = self.project(STACKS[0])
        with patch.object(demo.subprocess, 'run', side_effect=subprocess.TimeoutExpired('probe', 60)):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                status = demo.main(['check', '--project', str(project), '--report', str(self.root / 'timeout.json')])
        self.assertEqual(status, 2)
