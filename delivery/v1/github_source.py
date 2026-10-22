"""Retrieve exact immutable app releases with read-only GitHub credentials."""
import json
from pathlib import Path
import re
import shutil
import tempfile

from common import DeliveryError, HTTP, checksum, private_text
from release import eligible_release


class GitHubSource:
    """An allowlisted repository source; API failures never authorize deployment."""

    def __init__(self, config, http=None):
        self.config = config
        repository = config['repository']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise DeliveryError('Invalid repository')
        self.base = 'https://api.github.com/repos/' + repository
        self.headers = {'Authorization': 'Bearer ' + private_text(config['github_token_file']),
                        'Accept': 'application/vnd.github+json',
                        'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'lara-app-delivery-v1'}
        self.http = http or HTTP({'api.github.com', 'release-assets.githubusercontent.com',
                                  'objects.githubusercontent.com', 'github-releases.githubusercontent.com'})

    def get(self, path):
        """Fetch metadata only from this repository's GitHub API namespace."""
        return self.http.json(self.base + path, headers=self.headers)

    def asset(self, release, name, destination):
        """Verify API-provided size/digest while streaming an uploaded asset."""
        matches = [a for a in release.get('assets', []) if a.get('name') == name]
        if len(matches) != 1:
            raise DeliveryError('Required release asset is missing or ambiguous')
        asset = matches[0]
        digest = asset.get('digest', '')
        size = asset.get('size')
        if (asset.get('state') != 'uploaded' or type(asset.get('id')) is not int
                or not re.fullmatch(r'sha256:[0-9a-f]{64}', digest)
                or type(size) is not int or not 0 < size <= 2_000_000_000):
            raise DeliveryError('Unverified release asset metadata')
        headers = dict(self.headers, Accept='application/octet-stream')
        with self.http.open(self.base + '/releases/assets/' + str(asset['id']),
                            headers=headers) as response, Path(destination).open('xb') as output:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > size:
                    raise DeliveryError('Release asset exceeds declared size')
                output.write(chunk)
        if total != size or 'sha256:' + checksum(destination) != digest:
            raise DeliveryError('Release asset integrity failed')

    def candidate(self, current, release_root):
        """Select the latest release, coalescing superseded unpublished updates.

        A published release whose run is still finishing is retried next poll.
        Older/diverged releases never replace a current deployment.
        """
        releases = self.get('/releases?per_page=1')
        if not releases:
            return None
        release = releases[0]
        revision = release.get('target_commitish', '')
        if (not re.fullmatch(r'[0-9a-f]{40}', revision) or release.get('immutable') is not True
                or release.get('draft') is not False or release.get('prerelease') is not False):
            raise DeliveryError('Latest release is not an immutable production revision')
        if current['revision'] == revision:
            return None
        tag = self.get('/git/ref/tags/release-' + revision)['object']
        if tag.get('type') != 'commit':
            raise DeliveryError('Release tag must directly identify its commit')
        release['resolved_tag_sha'] = tag.get('sha')
        root = Path(release_root)
        with tempfile.TemporaryDirectory(prefix='.download-', dir=root) as temporary:
            folder = Path(temporary)
            self.asset(release, 'release.json', folder / 'release.json')
            if (folder / 'release.json').stat().st_size > 1024 * 1024:
                raise DeliveryError('Release manifest exceeds size limit')
            manifest = json.loads((folder / 'release.json').read_text())
            if (manifest.get('contract') != 1 or manifest.get('app') != self.config['app']
                    or manifest.get('revision') != revision
                    or type(manifest.get('run_id')) is not int
                    or not re.fullmatch(r'sha256:[0-9a-f]{64}', manifest.get('image_id', ''))
                    or set(manifest.get('artifacts', {})) != {'image.tar.gz', 'compose.yaml'}):
                raise DeliveryError('Unsupported app release manifest')
            run = self.get('/actions/runs/' + str(manifest['run_id']))
            # A publishing job may publish just before the workflow completes.
            if run.get('status') != 'completed':
                return None
            summaries = self.get('/commits/' + revision + '/pulls?per_page=100')
            prs = [self.get('/pulls/' + str(p['number'])) for p in summaries
                   if p.get('merge_commit_sha') == revision and type(p.get('number')) is int]
            if not eligible_release(release, run, prs, self.config['repository'], self.config['workflow']):
                raise DeliveryError('Release lacks successful exact-revision merge evidence')
            if self.get('/compare/' + current['revision'] + '...' + revision).get('status') != 'ahead':
                raise DeliveryError('Refusing an older or diverged release')
            for name, digest in manifest['artifacts'].items():
                if not re.fullmatch(r'[0-9a-f]{64}', digest):
                    raise DeliveryError('Invalid release payload checksum')
                self.asset(release, name, folder / name)
                if checksum(folder / name) != digest:
                    raise DeliveryError('Manifest payload checksum mismatch')
            destination = root / revision
            if destination.exists():
                if destination.is_symlink() or any(
                    (destination / name).is_symlink() or not (destination / name).is_file()
                    or checksum(destination / name) != checksum(folder / name)
                    for name in ('release.json', 'image.tar.gz', 'compose.yaml')
                ):
                    raise DeliveryError('Retained release directory failed integrity')
            else:
                shutil.move(str(folder), destination)
        return dict(manifest, directory=str(destination), compose=str(destination / 'compose.yaml'))
