"""Small private-file and HTTPS utilities; never log credentials or API bodies."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.parse
import urllib.request


class DeliveryError(RuntimeError):
    """An operator-safe failure message with no command output or credentials."""


def private_text(path):
    """Read an owner-only regular file, rejecting symlinks and broad permissions."""
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise DeliveryError('Credential file must be regular and owner-only')
    return path.read_text().strip()


def checksum(path):
    """Hash a payload without loading it into memory (Python 3.11+)."""
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save_json(path, data):
    """Atomically persist owner-only state, including durable recovery markers."""
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(data, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Require HTTPS allowlisted redirects; do not forward cross-host credentials."""

    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        if target.scheme != 'https' or target.hostname not in self.hosts:
            raise DeliveryError('Unexpected API redirect')
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and target.netloc != urllib.parse.urlsplit(req.full_url).netloc:
            redirected.remove_header('Authorization')
        return redirected


class HTTP:
    """Bounded HTTPS requests with explicit host allowlists and safe errors."""

    def __init__(self, hosts):
        self.hosts = set(hosts)
        self.opener = urllib.request.build_opener(SafeRedirect(self.hosts))

    def open(self, url, method='GET', headers=None, data=None):
        """Return a response stream; the caller closes it and bounds its contents."""
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname not in self.hosts:
            raise DeliveryError('Unexpected API origin')
        try:
            return self.opener.open(urllib.request.Request(url, data=data, method=method,
                                                         headers=headers or {}), timeout=60)
        except urllib.error.HTTPError as error:
            raise DeliveryError('API request failed (HTTP %s)' % error.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise DeliveryError('API connection failed') from None

    def json(self, url, method='GET', headers=None, data=None):
        """Read a limited JSON response; never expose a server error body."""
        with self.open(url, method, headers, data) as response:
            payload = response.read(8 * 1024 * 1024 + 1)
        if len(payload) > 8 * 1024 * 1024:
            raise DeliveryError('API metadata exceeds size limit')
        try:
            return json.loads(payload)
        except (ValueError, UnicodeError):
            raise DeliveryError('API returned invalid metadata') from None
