"""Download pinned public model assets with upstream size/hash verification."""
import hashlib
import json
import os
import urllib.request
from pathlib import Path

REPOSITORY = 'Systran/faster-whisper-large-v3'
REVISION = 'edaa852ec7e145841d8ffdb056a99866b5f0a478'
DESTINATION = Path(os.getenv('MODEL_DEST', '/models/large-v3'))
ASSETS = {'config.json', 'model.bin', 'preprocessor_config.json', 'tokenizer.json', 'vocabulary.json'}


def digest(path, asset):
    lfs = asset.get('lfs')
    checksum = hashlib.sha256() if lfs else hashlib.sha1()
    if not lfs:
        checksum.update(f'blob {path.stat().st_size}\0'.encode())
    with path.open('rb') as source:
        while chunk := source.read(1024 * 1024):
            checksum.update(chunk)
    return checksum.hexdigest()


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    url = f'https://huggingface.co/api/models/{REPOSITORY}/revision/{REVISION}?blobs=true'
    with urllib.request.urlopen(url, timeout=60) as response:
        metadata = json.load(response)
    if metadata['sha'] != REVISION:
        raise RuntimeError('Unexpected model revision')
    assets = {asset['rfilename']: asset for asset in metadata['siblings'] if asset['rfilename'] in ASSETS}
    if set(assets) != ASSETS:
        raise RuntimeError('Missing model assets in upstream manifest')
    for name, asset in assets.items():
        target = DESTINATION / name
        expected = asset['lfs']['sha256'] if asset.get('lfs') else asset['blobId']
        if target.exists() and target.stat().st_size == asset['size'] and digest(target, asset) == expected:
            print('Verified existing', name, flush=True)
            continue
        temporary = target.with_suffix(target.suffix + '.partial')
        print('Downloading', name, asset['size'], 'bytes', flush=True)
        with urllib.request.urlopen(f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{name}', timeout=120) as response, temporary.open('wb') as output:
            total = 0
            while chunk := response.read(4 * 1024 * 1024):
                output.write(chunk)
                total += len(chunk)
                if total % (128 * 1024 * 1024) == 0:
                    print(name, total, '/', asset['size'], flush=True)
        if temporary.stat().st_size != asset['size'] or digest(temporary, asset) != expected:
            raise RuntimeError('Model checksum mismatch: ' + name)
        temporary.replace(target)
        print('Verified', name, flush=True)
    (DESTINATION / 'source-manifest.json').write_text(json.dumps({'repository': REPOSITORY, 'revision': REVISION, 'assets': assets}, indent=2) + '\n')


if __name__ == '__main__':
    main()
