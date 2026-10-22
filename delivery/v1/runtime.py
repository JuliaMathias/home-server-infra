"""Serialized app delivery transactions with durable failure/recovery state."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess

from common import DeliveryError, save_json


def utc_now():
    """Return an aware timestamp; tests inject their own clock."""
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def app_lock(directory):
    """Serialize polling, backup and recovery operations for one app."""
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_mode & 0o077:
        raise DeliveryError('State directory must be private and not a symlink')
    lock = directory / 'operation.lock'
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise DeliveryError('Another app operation is already running') from None
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class HookAdapter:
    """Run a reviewed app-owned argv hook; never print child output/secrets."""

    def __init__(self, command, config_path):
        if not isinstance(command, list) or not command or not all(isinstance(v, str) for v in command):
            raise DeliveryError('Adapter must be an explicit command argument list')
        self.command = command
        self.config_path = str(config_path)

    def call(self, stage, current, candidate=None):
        """Pass public release metadata through environment; only backup returns JSON."""
        environment = dict(os.environ, LARA_DELIVERY_CONFIG=self.config_path,
                           LARA_DELIVERY_CURRENT=json.dumps(current),
                           LARA_DELIVERY_CANDIDATE=json.dumps(candidate))
        try:
            result = subprocess.run(self.command + [stage], env=environment,
                                    capture_output=True, timeout=900)
        except (OSError, subprocess.TimeoutExpired):
            raise DeliveryError('App adapter unavailable or timed out at ' + stage) from None
        if result.returncode:
            raise DeliveryError('App adapter failed at ' + stage)
        if stage == 'backup':
            try:
                return json.loads(result.stdout)
            except (ValueError, UnicodeError):
                raise DeliveryError('Backup adapter returned no verified receipt') from None
        return None


class Runner:
    """Keep the previous release/data and halt safely after migration uncertainty.

    The caller holds app_lock for selection and the entire operation. There is no
    automatic down-migration or image rollback after migration has started.
    """

    def __init__(self, directory, adapter, clock=utc_now):
        self.directory = Path(directory)
        self.adapter = adapter
        self.clock = clock

    def load(self, name):
        """Read a known state record; invalid/missing records stop the operation."""
        path = self.directory / (name + '.json')
        if path.is_symlink():
            raise DeliveryError('Refusing symlinked app state')
        return json.loads(path.read_text())

    def ready(self):
        """Require explicit bootstrap and operator resolution of interrupted work."""
        if not (self.directory / 'current.json').is_file():
            raise DeliveryError('Initialize the verified current release before activation')
        if (self.directory / 'transaction.json').exists():
            transaction = self.load('transaction')
            if transaction.get('status') in ('running', 'recovery_required'):
                raise DeliveryError('Operator recovery is required before further operations')
        return self.load('current')

    def record(self, stage, status='running', **extra):
        """Persist stage before side effects so process interruption fails closed."""
        save_json(self.directory / 'transaction.json',
                  dict(stage=stage, status=status, at=self.clock(), **extra))

    def backup(self, current):
        """Require a completed encrypted off-host receipt, preserving it locally."""
        receipt = self.adapter.call('backup', current)
        if (not isinstance(receipt, dict) or receipt.get('verified') is not True
                or receipt.get('app') != current['app'] or not receipt.get('id')
                or receipt.get('revision') != current['revision']):
            raise DeliveryError('Off-host backup was not verified')
        save_json(self.directory / 'last-backup.json', receipt)
        return receipt

    def daily_backup(self):
        """Take a consistent app-defined snapshot without running migrations."""
        current = self.ready()
        self.record('daily-backup')
        try:
            receipt = self.backup(current)
        except Exception:
            self.record('daily-backup', 'failed')
            raise
        self.record('daily-backup', 'success', backup_id=receipt['id'])
        return receipt

    def deploy(self, candidate):
        """Verify, pause writes, back up, migrate, activate and check readiness."""
        current = self.ready()
        if candidate['app'] != current['app']:
            raise DeliveryError('Candidate belongs to another application')
        if candidate['revision'] == current['revision']:
            return False
        paused = False
        migration_started = False
        receipt = None
        stage = 'verify'
        try:
            self.record(stage, candidate=candidate['revision'])
            self.adapter.call(stage, current, candidate)
            stage = 'pause'
            # A partially failed pause also requires resuming the previous app.
            paused = True
            self.record(stage, candidate=candidate['revision'])
            self.adapter.call(stage, current, candidate)
            stage = 'backup'
            self.record(stage, candidate=candidate['revision'])
            receipt = self.backup(current)
            stage = 'migrate'
            migration_started = True
            self.record(stage, candidate=candidate['revision'], backup_id=receipt['id'])
            self.adapter.call(stage, current, candidate)
            for stage in ('activate', 'health'):
                self.record(stage, candidate=candidate['revision'], backup_id=receipt['id'])
                self.adapter.call(stage, current, candidate)
            stage = 'record-current'
            save_json(self.directory / 'previous.json', current)
            save_json(self.directory / 'current.json', candidate)
            self.record('complete', 'success', candidate=candidate['revision'], backup_id=receipt['id'])
            return True
        except Exception:
            recovery = migration_started
            if migration_started:
                try:
                    self.adapter.call('stop', current, candidate)
                except Exception:
                    pass  # Preserve the failure/backup marker even if stopping also fails.
            elif paused:
                try:
                    self.adapter.call('resume', current, candidate)
                except Exception:
                    recovery = True
            self.record(stage, 'recovery_required' if recovery else 'failed',
                        candidate=candidate['revision'],
                        backup_id=receipt['id'] if receipt else None)
            raise DeliveryError('Update failed at ' + stage +
                                ('; operator recovery required' if recovery else '; previous release preserved')) from None
