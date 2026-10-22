"""Encrypt app-produced snapshots, verify off-host storage and gate expiry."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import re
import tempfile

from common import DeliveryError



def require_recovery(config, now=None):
    """Bind deployment/expiry approval to a real restore receipt and recipient."""
    now = now or datetime.now(timezone.utc)
    fingerprint = config.get('recipient_fingerprint', '')
    if (not re.fullmatch(r'(?:[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64})', fingerprint)
            or config.get('recovery_verified_for', '').upper() != fingerprint.upper()
            or not config.get('recovery_backup_id')):
        raise DeliveryError('Verified external-key restore receipt is required')
    try:
        verified = datetime.fromisoformat(config.get('recovery_verified_at') or '')
        if verified.tzinfo is None or verified > now:
            raise ValueError('Invalid restore clock')
    except (TypeError, ValueError):
        raise DeliveryError('Valid external-key recovery date is required') from None


def encrypted_backup(snapshot, app, current, config, store, now=None):
    """Keep plaintext in a private temporary directory and only upload ciphertext.

    snapshot(destination) is the app-owned consistency/manifest contract. gpg's
    configured keyring contains the public recipient; the private recovery key
    is held outside Lara. Expiry remains disabled until external-key recovery is
    explicitly verified by the operator after the actual restore exercise.
    """
    now = now or datetime.now(timezone.utc)
    if config.get('expiry_enabled') is True:
        require_recovery(config, now)
    if not re.fullmatch(r'(?:[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64})', config.get('recipient_fingerprint', '')):
        raise DeliveryError('A full encryption recipient fingerprint is required')
    with tempfile.TemporaryDirectory(prefix='.backup-', dir=config['scratch_dir']) as temporary:
        folder = Path(temporary)
        plain = folder / 'snapshot.tar'
        cipher = folder / 'snapshot.gpg'
        snapshot(plain)
        if not plain.is_file() or plain.is_symlink() or not plain.stat().st_size:
            raise DeliveryError('Application snapshot is empty or unavailable')
        command = [config.get('gpg', '/usr/bin/gpg'), '--homedir', config['public_keyring'],
                   '--batch', '--no-tty', '--trust-model', 'always', '--output', str(cipher),
                   '--recipient', config['recipient_fingerprint'], '--encrypt', str(plain)]
        try:
            subprocess.run(command, capture_output=True, check=True, timeout=300)
        except (OSError, subprocess.SubprocessError):
            raise DeliveryError('Backup encryption failed') from None
        receipt = store.upload(cipher, app, current['revision'], now.isoformat())
    # Expiry failure must be reported; a valid new backup is still retained.
    if config.get('expiry_enabled') is True:
        store.expire(app, config['minimum_count'], config['minimum_days'], now,
                     config.get('protected_backup_ids', []))
    return receipt
