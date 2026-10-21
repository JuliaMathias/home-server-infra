"""Fetch the pinned candidate atomically and verify its size and SHA-256."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import urllib.request

from candidate_config import candidate_settings


def checksum(path):
    """Return the full-file SHA-256 without loading weights into RAM."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    """Download or verify the immutable model candidate under an exclusive lock."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=Path(__file__).with_name('candidate.json'))
    args = parser.parse_args()
    candidate, directory, _, _ = candidate_settings(args.candidate)
    directory = Path(os.environ.get('MODEL_DEST', directory))
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.download.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest_path = directory / 'source-manifest.json'
        if manifest_path.exists():
            existing = json.loads(manifest_path.read_text())
            if any(existing.get(k) != candidate[k] for k in ('repository','revision','filename','bytes','sha256')):
                raise RuntimeError('Model directory belongs to another candidate; preserve its manifest')
        destination = directory / candidate['filename']
        if destination.exists():
            if destination.stat().st_size == candidate['bytes'] and checksum(destination) == candidate['sha256']:
                if not manifest_path.exists():
                    manifest_path.write_text(json.dumps(candidate, indent=2) + '\n')
                print('Verified existing model', flush=True)
                return
            raise RuntimeError('Existing model differs; preserve it and investigate before replacement')
        temporary = directory / (candidate['filename'] + '.partial')
        url = f"https://huggingface.co/{candidate['repository']}/resolve/{candidate['revision']}/{candidate['filename']}"
        digest = hashlib.sha256()
        count = 0
        with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as stream:
            while chunk := response.read(8 * 1024 * 1024):
                stream.write(chunk)
                digest.update(chunk)
                count += len(chunk)
                if count % (256 * 1024 * 1024) == 0:
                    print(f'Downloaded {count}/{candidate["bytes"]} bytes', flush=True)
        if count != candidate['bytes'] or digest.hexdigest() != candidate['sha256']:
            raise RuntimeError('Downloaded model size/hash verification failed')
        temporary.replace(destination)
        (directory / 'source-manifest.json').write_text(json.dumps(candidate, indent=2) + '\n')
        print('Model size and SHA-256 verified:', destination, flush=True)


if __name__ == '__main__':
    main()
