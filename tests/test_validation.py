import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.validate_repo import ROOT, SKILL, validate


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ('plugins', '.agents', '.claude-plugin', 'evals'):
            shutil.copytree(ROOT / directory, self.root / directory)
        for filename in ('README.md', 'LICENSE'):
            shutil.copyfile(ROOT / filename, self.root / filename)

    def test_repository_is_valid(self):
        self.assertEqual(validate(self.root), [])

    def test_local_copy_drift_is_rejected(self):
        local = self.root / '.agents/skills/python-structured-logging'
        (local / 'SKILL.md').write_text('outdated')
        self.assertTrue(any('Skill copies differ' in e for e in validate(self.root)))

    def test_extra_local_resource_is_rejected(self):
        local = self.root / '.agents/skills/python-structured-logging'
        (local / 'unexpected.md').write_text('stale resource')
        self.assertTrue(any('Skill copies differ' in e for e in validate(self.root)))

    def test_generated_files_do_not_count_as_drift(self):
        local = self.root / '.agents/skills/python-structured-logging'
        (local / '__pycache__').mkdir(exist_ok=True)
        (local / '__pycache__/example.pyc').write_bytes(b'cache')
        (local / '.DS_Store').write_bytes(b'editor')
        self.assertEqual(validate(self.root), [])

    def test_malformed_yaml_is_rejected(self):
        (self.root / SKILL / 'SKILL.md').write_text('---\nname: [\ndescription: broken\n---\n')
        self.assertTrue(validate(self.root))

    def test_wrong_name_is_rejected(self):
        path = self.root / SKILL / 'SKILL.md'
        path.write_text(path.read_text().replace('name: python-structured-logging', 'name: different-name', 1))
        self.assertTrue(any('name must match' in e for e in validate(self.root)))

    def test_missing_resource_is_rejected(self):
        (self.root / SKILL / 'examples/stdlib/good.py').unlink()
        self.assertTrue(any('missing or external local resource' in e for e in validate(self.root)))

    def test_wrong_marketplace_path_is_rejected(self):
        path = self.root / '.agents/plugins/marketplace.json'
        data = json.loads(path.read_text())
        data['plugins'][0]['source'] = './missing'
        path.write_text(json.dumps(data))
        self.assertTrue(any('name/source' in e for e in validate(self.root)))

    def test_missing_eval_fixture_is_rejected(self):
        path = self.root / 'evals/cases.json'
        data = json.loads(path.read_text())
        data['cases'][0]['fixtures'] = ['evals/fixtures/missing.py']
        path.write_text(json.dumps(data))
        self.assertTrue(any('missing fixture' in e for e in validate(self.root)))

    def test_invalid_ui_prompt_is_reported_without_crashing(self):
        path = self.root / SKILL / 'agents/openai.yaml'
        path.write_text('interface:\n  default_prompt: 123\n')
        self.assertTrue(any('default_prompt' in e for e in validate(self.root)))
