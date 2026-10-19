"""Fetch the pinned candidate atomically and verify its size and SHA-256."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import urllib.request


def checksum(path):
    """Return the full-file SHA-256 without loading weights into RAM."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    """Download or verify the immutable model candidate under an exclusive lock."""
    candidate = json.loads(Path(__file__).with_name('candidate.json').read_text())
    directory = Path(os.environ.get('MODEL_DEST', '/srv/lara/ai/models/qwen3-14b'))
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.download.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        destination = directory / candidate['filename']
        if destination.exists():
            if destination.stat().st_size == candidate['bytes'] and checksum(destination) == candidate['sha256']:
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
