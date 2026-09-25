import copy
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'evals/worker_consumer'
sys.path.insert(0,str(HERE))
from evaluate import evaluate, grade
from repair import repair


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.project=Path(cls.temp.name)/'fixed'
        shutil.copytree(HERE/'template',cls.project)
        cls.bad=evaluate(HERE/'template')
        repair(cls.project)
        cls.good=evaluate(cls.project)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_baseline_contracts_and_logging_defects(self):
        results={c['id']:c['passed'] for c in self.bad['criteria']}
        self.assertTrue(results['business_contract'])
        self.assertTrue(results['retry_ack_contract'])
        self.assertTrue(results['cancellation_contract'])
        for name in ('whole_runtime_json','payload_credential_exception_safety','context_cleanup',
                     'single_failure_ownership','formatter_cycle','formatter_object'):
            self.assertFalse(results[name],name)

    def test_minimal_repair(self):
        self.assertTrue(self.good['passed'],self.good['criteria'])

    def test_observable_mutations(self):
        def failure(name, mutate):
            observed=copy.deepcopy(self.good['observations']); mutate(observed)
            result={c['id']:c for c in grade(observed)['criteria']}
            self.assertFalse(result[name]['passed'],result[name])
        failure('formatter_cycle',lambda o:o['cycle']['metadata'].update(emission={'stdout':'','stderr':''}))
        failure('formatter_object',lambda o:o['object']['metadata'].update(raised='TypeError'))
        failure('formatter_nonfinite',lambda o:o['nonfinite'].update(stderr=o['nonfinite']['stderr']+'{"event":"x","level":"info","n":NaN}\n'))
        failure('whole_runtime_json',lambda o:o['workload'].update(stdout='raw runtime error\n'))
        failure('retry_ack_contract',lambda o:o['workload']['metadata']['dispositions'].append(['retry','ack',1]))
        failure('payload_credential_exception_safety',lambda o:o['workload'].update(stdout='SYNTHETIC_TOKEN_SECRET\n'))

    def test_pre_freeze_review_regressions(self):
        def remove_records(observed, predicate):
            import json
            for stream in ('stdout','stderr'):
                observed['workload'][stream]='\n'.join(line for line in observed['workload'][stream].splitlines()
                                                       if not predicate(json.loads(line)))
        for name, mutate in [
            ('context_cleanup', lambda o:remove_records(o,lambda r:r['event']=='probe.scope_clear')),
            ('concurrent_nested_context',lambda o:remove_records(o,lambda r:r['event']=='probe.nested')),
            ('background_failure',lambda o:o['workload']['metadata'].update(audit_completed=['audit'])),
            ('single_failure_ownership',lambda o:o['workload'].update(stdout='{"event":"runtime.failed","level":"error"}\n')),
            ('formatter_cycle',lambda o:o['cycle']['metadata'].update(emission={'stdout':'','stderr':''})),
        ]:
            with self.subTest(name=name):
                observed=copy.deepcopy(self.good['observations']); mutate(observed)
                self.assertFalse(next(c for c in grade(observed)['criteria'] if c['id']==name)['passed'])

    def test_safe_fallback_and_optional_lifecycle(self):
        observed=copy.deepcopy(self.good['observations'])
        for case in ('nonfinite','cycle','object','key'):
            observed[case]['stderr']='{"event":"serialization.fallback","level":"warning"}\n{"event":"probe.recovery","level":"info"}\n'
            observed[case]['stdout']=''
            observed[case]['metadata']['emission']={'stdout':'','stderr':'{"event":"serialization.fallback","level":"warning"}\n'}
        for stream in ('stdout','stderr'):
            observed['workload'][stream]='\n'.join(line for line in observed['workload'][stream].splitlines() if 'runtime.lifecycle' not in line)
        self.assertTrue(grade(observed)['passed'])
