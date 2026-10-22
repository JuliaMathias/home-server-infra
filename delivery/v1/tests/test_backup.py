"""Fake-transport Drive and encryption orchestration behavior tests."""
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backup import encrypted_backup, require_recovery
from common import DeliveryError
from drive import DRIVE_SCOPE, DriveStore


class Response(io.BytesIO):
    """A context-managed upload-session or ciphertext response."""
    def __init__(self, content=b'', location=None):
        super().__init__(content)
        self.headers = {'Location':location} if location else {}


class FakeDriveHTTP:
    """Record protocol calls without contacting Google or using a real account."""
    def __init__(self):
        self.calls=[]
        self.cipher=b''
        self.corrupt=False
        self.shared=False
        self.scope=DRIVE_SCOPE
        self.files=[]
        self.metadata={}

    def json(self,url,method='GET',headers=None,data=None):
        payload = json.loads(data) if isinstance(data,bytes) and data.startswith(b'{') else data
        self.calls.append((method,url,payload))
        if url.endswith('/token'): return {'access_token':'synthetic-access','scope':self.scope}
        if '/files/folder?' in url: return {'id':'folder','mimeType':'application/vnd.google-apps.folder','shared':self.shared,'trashed':False}
        if method=='PUT':
            self.cipher=data.read()
            return {'id':'cipher-object'}
        if '/files?' in url: return {'files':self.files}
        if '/files/cipher-object?' in url and method=='GET': return self.metadata
        return {'id':'cipher-object'}

    def open(self,url,method='GET',headers=None,data=None):
        self.calls.append((method,url,json.loads(data) if data else None))
        if method=='POST': return Response(location='https://www.googleapis.com/upload/drive/v3/files?upload_id=synthetic')
        return Response(b'corrupt' if self.corrupt else self.cipher)


class BackupTest(unittest.TestCase):
    """Count only verified encrypted backups and enforce recovery before expiry."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.credentials=self.root/'drive.json'
        self.credentials.write_text(json.dumps({'folder_id':'folder','client_id':'synthetic',
            'client_secret':'synthetic','refresh_token':'synthetic'}))
        self.credentials.chmod(0o600)
        self.http=FakeDriveHTTP()
        self.now=datetime(2026,10,22,6,tzinfo=timezone.utc)
        self.path=self.root/'snapshot.gpg'
        self.path.write_bytes(b'synthetic-ciphertext')

    def store(self):
        return DriveStore(self.credentials,self.http)

    def test_upload_is_verified_before_its_receipt_is_marked_complete(self):
        receipt=self.store().upload(self.path,'notey','a'*40,self.now.isoformat())
        self.assertTrue(receipt['verified'])
        calls=self.http.calls
        download=next(i for i,c in enumerate(calls) if '?alt=media' in c[1])
        marked=next(i for i,c in enumerate(calls) if c[0]=='PATCH' and c[2].get('appProperties',{}).get('status')=='verified')
        self.assertLess(download,marked)
        creation=next(c[2] for c in calls if c[0]=='POST' and 'uploadType=resumable' in c[1])
        self.assertEqual(creation['parents'],['folder'])
        self.assertEqual(creation['appProperties']['status'],'incomplete')

    def test_corrupt_offhost_bytes_do_not_produce_verified_receipt(self):
        self.http.corrupt=True
        with self.assertRaises(DeliveryError): self.store().upload(self.path,'notey','a'*40,self.now.isoformat())
        self.assertFalse(any(c[0]=='PATCH' for c in self.http.calls))

    def test_recovery_download_requires_verified_app_folder_and_matching_bytes(self):
        self.http.cipher=self.path.read_bytes()
        properties={'app':'notey','contract':'1','status':'verified',
                    'sha256':hashlib.sha256(self.http.cipher).hexdigest()}
        self.http.metadata={'parents':['folder'],'trashed':False,'appProperties':properties}
        restored=self.root/'download.gpg'
        self.store().download('cipher-object','notey',restored)
        self.assertEqual(restored.read_bytes(),self.http.cipher)
        self.assertEqual(restored.stat().st_mode & 0o777,0o600)
        for key,value in (('app','other'),('status','incomplete')):
            self.http.metadata['appProperties']=dict(properties,**{key:value})
            with self.subTest(key=key), self.assertRaises(DeliveryError):
                self.store().download('cipher-object','notey',self.root/('reject-'+key))
        self.http.metadata['appProperties']=properties
        self.http.corrupt=True
        with self.assertRaises(DeliveryError):
            self.store().download('cipher-object','notey',self.root/'corrupt.gpg')

    def test_shared_folder_or_broad_scope_is_rejected(self):
        self.http.shared=True
        with self.assertRaises(DeliveryError): self.store()
        self.http.shared=False
        self.http.scope='https://www.googleapis.com/auth/drive'
        with self.assertRaises(DeliveryError): self.store()

    def test_expiry_targets_only_old_app_scoped_objects_and_moves_to_trash(self):
        for index in range(3):
            self.http.files.append({'id':'backup'+str(index),'appProperties':{
                'app':'notey','contract':'1','status':'verified',
                'created_at':(self.now-timedelta(hours=200+index)).isoformat()}})
        result=self.store().expire('notey',2,5,self.now)
        self.assertEqual(result,['backup2'])
        patches=[c for c in self.http.calls if c[0]=='PATCH']
        self.assertEqual(len(patches),1)
        self.assertIn('/files/backup2?',patches[0][1])
        self.assertEqual(patches[0][2],{'trashed':True})
        self.assertFalse(any(c[0]=='DELETE' for c in self.http.calls))

    def test_mixed_app_metadata_prevents_all_expiry(self):
        self.http.files=[{'id':'other','appProperties':{'app':'other','contract':'1'}}]
        with self.assertRaises(DeliveryError): self.store().expire('notey',30,5,self.now)
        self.assertFalse(any(c[0]=='PATCH' for c in self.http.calls))

    def test_encryption_precedes_upload_and_scratch_plaintext_is_removed(self):
        store=self.store()
        config={'scratch_dir':str(self.root),'public_keyring':str(self.root/'public'),
                'recipient_fingerprint':'A'*40,'expiry_enabled':False}
        def encrypt(command,**kwargs):
            self.assertEqual(command[-2],'--encrypt')
            self.assertEqual(Path(command[-1]).read_bytes(),b'synthetic-plaintext')
            Path(command[command.index('--output')+1]).write_bytes(b'encrypted-test-output')
        with patch('backup.subprocess.run',side_effect=encrypt):
            encrypted_backup(lambda path:path.write_bytes(b'synthetic-plaintext'), 'notey',
                             {'revision':'a'*40},config,store,self.now)
        self.assertEqual(self.http.cipher,b'encrypted-test-output')
        self.assertFalse(list(self.root.glob('.backup-*')))

    def test_encryption_failure_prevents_upload(self):
        store=self.store()
        before=len(self.http.calls)
        config={'scratch_dir':str(self.root),'public_keyring':'unused','recipient_fingerprint':'A'*40}
        with patch('backup.subprocess.run',side_effect=subprocess.CalledProcessError(2,['gpg'])):
            with self.assertRaises(DeliveryError):
                encrypted_backup(lambda path:path.write_bytes(b'plain'),'notey',{'revision':'a'*40},config,store,self.now)
        self.assertEqual(len(self.http.calls),before)

    def test_expiry_cannot_start_without_external_recovery_evidence(self):
        config={'expiry_enabled':True}
        with self.assertRaises(DeliveryError):
            encrypted_backup(lambda path:None,'notey',{'revision':'a'*40},config,None,self.now)


class RecoveryGateTest(unittest.TestCase):
    """A key change or invalid/unrecorded restore blocks deployment and expiry."""
    def test_receipt_is_bound_to_the_current_encryption_key(self):
        now=datetime(2026,10,22,6,tzinfo=timezone.utc)
        config={'recipient_fingerprint':'A'*40,'recovery_verified_for':'A'*40,
                'recovery_backup_id':'synthetic','recovery_verified_at':'2026-10-22T05:00:00+00:00'}
        require_recovery(config,now)
        for key,value in (('recovery_verified_for','B'*40),('recovery_backup_id',''),
                          ('recovery_verified_at','2026-10-23T05:00:00+00:00'),
                          ('recovery_verified_at','2026-10-22')):
            with self.subTest(key=key), self.assertRaises(DeliveryError):
                require_recovery(dict(config,**{key:value}),now)
