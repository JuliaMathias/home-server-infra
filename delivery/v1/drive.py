"""App-scoped encrypted-object storage using Google Drive's resumable API.

Only ciphertext is accepted by the backup orchestration layer. This adapter
holds an OAuth refresh credential, not a backup decryption key. Expiry moves
selected integration-owned objects to Drive Trash; it never empties Trash.
"""
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import uuid

from common import DeliveryError, HTTP, checksum, private_text
from retention import retention_candidates

DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive.file'


def object_id(identifier):
    """Reject API identifiers containing path/query syntax."""
    if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', identifier):
        raise DeliveryError('Invalid Drive object identity')
    return identifier


class DriveStore:
    """Use one app's private folder and dedicated drive.file OAuth credential."""

    def __init__(self, credential_file, http=None):
        credential = json.loads(private_text(credential_file))
        self.folder = object_id(credential['folder_id'])
        self.http = http or HTTP({'oauth2.googleapis.com', 'www.googleapis.com'})
        token = self.http.json('https://oauth2.googleapis.com/token', method='POST',
                               headers={'Content-Type': 'application/x-www-form-urlencoded'},
                               data=urllib.parse.urlencode({
                                   'client_id': credential['client_id'],
                                   'client_secret': credential['client_secret'],
                                   'refresh_token': credential['refresh_token'],
                                   'grant_type': 'refresh_token'}).encode())
        if token.get('scope') and set(token['scope'].split()) != {DRIVE_SCOPE}:
            raise DeliveryError('Unexpected Google OAuth scope')
        access = token.get('access_token')
        if not isinstance(access, str) or not access:
            raise DeliveryError('Google authorization did not return an access token')
        self.headers = {'Authorization': 'Bearer ' + access}
        folder = self.json('/files/' + self.folder + '?fields=id,mimeType,trashed,shared')
        if (folder.get('id') != self.folder or folder.get('trashed') is not False
                or folder.get('shared') is not False
                or folder.get('mimeType') != 'application/vnd.google-apps.folder'):
            raise DeliveryError('Backup folder is unavailable, shared or not a private folder')

    def json(self, path, method='GET', data=None):
        """Call the fixed Drive namespace; request bodies are never logged."""
        headers = dict(self.headers)
        payload = None
        if data is not None:
            headers['Content-Type'] = 'application/json'
            payload = json.dumps(data).encode()
        return self.http.json('https://www.googleapis.com/drive/v3' + path,
                              method=method, headers=headers, data=payload)

    def verify_bytes(self, identifier, expected_hash, destination=None):
        """Download and hash ciphertext; optionally save it to a new private file."""
        identifier = object_id(identifier)
        digest = hashlib.sha256()
        output = None
        try:
            if destination is not None:
                output = Path(destination).open('xb')
                Path(destination).chmod(0o600)
            with self.http.open('https://www.googleapis.com/drive/v3/files/' + identifier + '?alt=media',
                                headers=self.headers) as response:
                while chunk := response.read(1024 * 1024):
                    digest.update(chunk)
                    if output:
                        output.write(chunk)
        finally:
            if output:
                output.close()
        if digest.hexdigest() != expected_hash:
            raise DeliveryError('Off-host encrypted backup checksum mismatch')

    def upload(self, path, app, revision, created_at):
        """Upload ciphertext, download-verify it, then mark its receipt complete."""
        path = Path(path)
        digest = checksum(path)
        metadata = {'name': app + '-' + uuid.uuid4().hex + '.gpg',
                    'parents': [self.folder], 'appProperties': {
                        'app': app, 'contract': '1', 'revision': revision,
                        'created_at': created_at, 'status': 'incomplete', 'sha256': digest}}
        headers = dict(self.headers, **{'Content-Type': 'application/json',
                       'X-Upload-Content-Type': 'application/octet-stream',
                       'X-Upload-Content-Length': str(path.stat().st_size)})
        with self.http.open('https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&fields=id',
                            method='POST', headers=headers, data=json.dumps(metadata).encode()) as response:
            location = response.headers.get('Location', '')
        parsed = urllib.parse.urlsplit(location)
        if (parsed.scheme != 'https' or parsed.netloc != 'www.googleapis.com'
                or not parsed.path.startswith('/upload/drive/v3/files')):
            raise DeliveryError('Unexpected Google upload session origin')
        # urllib/http.client streams a file object when Content-Length is supplied.
        with path.open('rb') as stream:
            result = self.http.json(location, method='PUT',
                                    headers=dict(self.headers, **{'Content-Type': 'application/octet-stream',
                                                   'Content-Length': str(path.stat().st_size)}), data=stream)
        identifier = object_id(result['id'])
        self.verify_bytes(identifier, digest)
        properties = dict(metadata['appProperties'], status='verified')
        self.json('/files/' + identifier + '?fields=id', 'PATCH', {'appProperties': properties})
        return {'id': identifier, 'app': app, 'revision': revision,
                'created_at': created_at, 'sha256': digest, 'verified': True}


    def download(self, identifier, app, destination):
        """Retrieve one verified app-scoped ciphertext for external-key recovery."""
        identifier=object_id(identifier)
        metadata=self.json('/files/'+identifier+'?fields=id,parents,trashed,appProperties')
        properties=metadata.get('appProperties',{})
        if (metadata.get('parents') != [self.folder] or metadata.get('trashed') is not False
                or properties.get('app') != app or properties.get('contract') != '1'
                or properties.get('status') != 'verified'
                or not re.fullmatch(r'[0-9a-f]{64}',properties.get('sha256',''))):
            raise DeliveryError('Backup is not a verified object in this app folder')
        self.verify_bytes(identifier,properties['sha256'],destination)
        return properties

    def receipts(self, app):
        """List only this integration's tagged objects within its private folder."""
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,62}', app):
            raise DeliveryError('Invalid backup application identity')
        query = "'%s' in parents and trashed = false and appProperties has { key='app' and value='%s' }" % (self.folder, app)
        parameters = {'q': query, 'spaces': 'drive', 'pageSize': 1000,
                      'fields': 'nextPageToken,files(id,appProperties)'}
        result = []
        pages = set()
        while True:
            page = self.json('/files?' + urllib.parse.urlencode(parameters))
            for item in page['files']:
                properties = item['appProperties']
                if properties.get('app') != app or properties.get('contract') != '1':
                    raise DeliveryError('Unexpected backup namespace')
                result.append({'id': object_id(item['id']), 'app': app,
                               'status': properties['status'], 'created_at': properties['created_at']})
            token = page.get('nextPageToken')
            if not token:
                return result
            if token in pages:
                raise DeliveryError('Repeated Drive listing page')
            pages.add(token)
            parameters['pageToken'] = token

    def expire(self, app, minimum_count, minimum_days, now, protected=()):
        """Move only a fully evaluated app-specific candidate list to Drive Trash."""
        candidates = retention_candidates(self.receipts(app), app, minimum_count,
                                           minimum_days, now, protected)
        for identifier in candidates:
            self.json('/files/' + object_id(identifier) + '?fields=id,trashed',
                      'PATCH', {'trashed': True})
        return candidates
