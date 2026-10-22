"""Behavioral transaction/locking tests using deterministic app hooks."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DeliveryError, save_json
from runtime import Runner, app_lock


class FakeApp:
    """Observe app phase order and inject failures without external services."""
    def __init__(self, failure=None, verified=True):
        self.calls = []
        self.failure = failure
        self.verified = verified

    def call(self, phase, current, candidate=None):
        self.calls.append(phase)
        if phase == self.failure:
            raise RuntimeError('private diagnostics must not escape')
        if phase == 'backup':
            return {'id': 'synthetic-backup', 'verified': self.verified,
                    'app': current['app'], 'revision': current['revision']}


class TransactionTest(unittest.TestCase):
    """Preserve releases/data and refuse unsafe continuation after migration."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.current = {'app': 'notey', 'revision': 'a'*40, 'image_id': 'sha256:'+'a'*64}
        self.candidate = {'app': 'notey', 'revision': 'b'*40, 'image_id': 'sha256:'+'b'*64}
        save_json(self.root/'current.json', self.current)
        self.app = FakeApp()
        self.runner = Runner(self.root, self.app, lambda: '2026-10-22T06:00:00+00:00')

    def test_success_backs_up_before_migration_and_preserves_previous(self):
        self.assertTrue(self.runner.deploy(self.candidate))
        self.assertEqual(self.app.calls, ['verify','pause','backup','migrate','activate','health'])
        self.assertEqual(self.runner.load('previous'), self.current)
        self.assertEqual(self.runner.ready(), self.candidate)
        self.assertEqual(self.runner.load('last-backup')['id'], 'synthetic-backup')

    def test_verify_failure_does_not_pause_or_migrate(self):
        self.app.failure = 'verify'
        with self.assertRaises(DeliveryError):
            self.runner.deploy(self.candidate)
        self.assertEqual(self.app.calls, ['verify'])
        self.assertEqual(self.runner.ready(), self.current)

    def test_unverified_backup_resumes_previous_without_migrating(self):
        self.app.verified = False
        with self.assertRaises(DeliveryError):
            self.runner.deploy(self.candidate)
        self.assertEqual(self.app.calls, ['verify','pause','backup','resume'])
        self.assertEqual(self.runner.ready(), self.current)

    def test_failed_backup_resumes_previous_and_hides_diagnostics(self):
        self.app.failure = 'backup'
        with self.assertRaises(DeliveryError) as caught:
            self.runner.deploy(self.candidate)
        self.assertNotIn('private diagnostics', str(caught.exception))
        self.assertNotIn('migrate', self.app.calls)
        self.assertEqual(self.runner.ready(), self.current)

    def test_migration_and_health_failures_require_recovery_not_image_rollback(self):
        for failure in ('migrate', 'activate', 'health'):
            with self.subTest(failure=failure):
                (self.root/'transaction.json').unlink(missing_ok=True)
                self.app = FakeApp(failure)
                runner = Runner(self.root, self.app)
                with self.assertRaises(DeliveryError):
                    runner.deploy(self.candidate)
                self.assertEqual(self.app.calls[-1], 'stop')
                self.assertNotIn('resume', self.app.calls)
                self.assertEqual(runner.load('current'), self.current)
                self.assertEqual(runner.load('transaction')['backup_id'], 'synthetic-backup')
                with self.assertRaises(DeliveryError):
                    runner.ready()

    def test_interrupted_transaction_blocks_subsequent_work(self):
        self.runner.record('migrate')
        with self.assertRaises(DeliveryError):
            Runner(self.root, self.app).daily_backup()
        self.assertEqual(self.app.calls, [])

    def test_same_revision_is_a_noop_and_other_app_is_rejected(self):
        self.assertFalse(self.runner.deploy(self.current))
        with self.assertRaises(DeliveryError):
            self.runner.deploy(dict(self.candidate, app='other'))
        self.assertEqual(self.app.calls, [])

    def test_daily_backup_never_runs_migrations(self):
        self.runner.daily_backup()
        self.assertEqual(self.app.calls, ['backup'])
        self.assertEqual(self.runner.ready(), self.current)

    def test_overlapping_process_cannot_acquire_the_app_lock(self):
        directory = str(Path(__file__).resolve().parents[1])
        code = 'import sys; sys.path.insert(0, sys.argv[1]); from runtime import app_lock; with_lock=app_lock(sys.argv[2]); with_lock.__enter__()'
        with app_lock(self.root):
            result = subprocess.run([sys.executable,'-c',code,directory,str(self.root)],capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'already running', result.stderr)
        with app_lock(self.root):
            pass
