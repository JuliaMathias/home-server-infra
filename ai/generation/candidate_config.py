"""Resolve explicit evaluation candidates without changing the default model.

Metadata is a trusted operator input, not an HTTP API. The host directory and
container path are derived from safe single path components under the fixed
model roots. Weight verification belongs to the downloader and run manifest.
"""
import json
from pathlib import Path


def candidate_settings(path, models_root=Path('/srv/lara/ai/models')):
    """Return metadata, host directory, container model path and runtime alias.

    Older candidate files retain the original directory and alias defaults.
    Reject path traversal and malformed pinned identities before file/network IO.
    """
    import re
    candidate = json.loads(Path(path).read_text())
    directory = candidate.get('model_directory', 'qwen3-14b')
    filename = candidate['filename']
    for component in (directory, filename):
        if not isinstance(component, str) or component in ('', '.', '..') or not re.fullmatch(r'[A-Za-z0-9_.-]+', component):
            raise ValueError('Model directory/filename must be safe single path components')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', candidate['repository']):
        raise ValueError('Invalid model repository')
    if not re.fullmatch(r'[a-f0-9]{40}', candidate['revision']) or not re.fullmatch(r'[a-f0-9]{64}', candidate['sha256']):
        raise ValueError('Expected pinned revision and SHA-256')
    if type(candidate['bytes']) is not int or candidate['bytes'] <= 0:
        raise ValueError('Expected positive weight size')
    alias = candidate.get('alias', 'qwen3-14b-trial')
    if not isinstance(alias, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', alias):
        raise ValueError('Invalid model alias')
    return candidate, models_root / directory, '/models/' + directory + '/' + filename, alias
