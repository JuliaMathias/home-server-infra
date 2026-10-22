"""Authenticated metadata/asset contract tests with a fake HTTP transport."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import DeliveryError, SafeRedirect
from github_source import GitHubSource


class FakeHTTP:
    """Serve synthetic GitHub metadata and byte streams while observing requests."""
    def __init__(self, metadata, payloads):
        self.metadata = metadata
        self.payloads = payloads
        self.downloads = []

    def json(self, url, **kwargs):
        return deepcopy(self.metadata[url.split('/repos/owner/app',1)[1]])

    def open(self, url, **kwargs):
        identifier = int(url.rsplit('/',1)[1])
        self.downloads.append(identifier)
        return io.BytesIO(self.payloads[identifier])


class SourceTest(unittest.TestCase):
    """Only verified, forward, exact-source release assets can reach activation."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        token = self.root/'token'
        token.write_text('synthetic-token')
        token.chmod(0o600)
        self.sha = 'b'*40
        self.manifest = {'contract':1,'app':'notey','revision':self.sha,'run_id':12,
                         'image_id':'sha256:'+'b'*64, 'artifacts':{
                             'image.tar.gz':hashlib.sha256(b'image').hexdigest(),
                             'compose.yaml':hashlib.sha256(b'compose').hexdigest()}}
        self.payloads = {1:json.dumps(self.manifest).encode(),2:b'image',3:b'compose'}
        assets = [{'id':i,'name':name,'size':len(self.payloads[i]),'state':'uploaded',
                   'digest':'sha256:'+hashlib.sha256(self.payloads[i]).hexdigest()}
                  for i,name in enumerate(('release.json','image.tar.gz','compose.yaml'),1)]
        self.metadata = {
            '/releases?per_page=1':[{'target_commitish':self.sha,'tag_name':'release-'+self.sha,
                                  'immutable':True,'draft':False,'prerelease':False,'assets':assets}],
            '/git/ref/tags/release-'+self.sha:{'object':{'type':'commit','sha':self.sha}},
            '/actions/runs/12':{'head_sha':self.sha,'head_branch':'main','event':'push','status':'completed',
                              'conclusion':'success','path':'.github/workflows/ci.yml','repository':{'full_name':'owner/app'}},
            '/commits/'+self.sha+'/pulls?per_page=100':[{'number':5,'merge_commit_sha':self.sha}],
            '/pulls/5':{'merged_at':'2026-10-22','merge_commit_sha':self.sha,'merged_by':{'type':'User'},
                       'base':{'ref':'main','repo':{'full_name':'owner/app'}}},
            '/compare/'+'a'*40+'...'+self.sha:{'status':'ahead'}}
        self.http = FakeHTTP(self.metadata,self.payloads)
        self.source = GitHubSource({'app':'notey','repository':'owner/app','workflow':'.github/workflows/ci.yml',
                                    'github_token_file':str(token)},self.http)
        self.current = {'revision':'a'*40}

    def test_exact_verified_release_downloads_and_can_retry_from_identical_cache(self):
        result = self.source.candidate(self.current,self.root)
        self.assertEqual(Path(result['compose']).read_bytes(),b'compose')
        self.assertEqual(self.source.candidate(self.current,self.root)['image_id'],self.manifest['image_id'])

    def test_pending_ci_never_downloads_image(self):
        self.metadata['/actions/runs/12']['status']='in_progress'
        self.assertIsNone(self.source.candidate(self.current,self.root))
        self.assertEqual(self.http.downloads,[1])

    def test_corrupt_asset_and_missing_digest_are_rejected(self):
        self.payloads[2]=b'wrong'
        with self.assertRaises(DeliveryError): self.source.candidate(self.current,self.root)
        self.assertFalse((self.root/self.sha).exists())
        self.metadata['/releases?per_page=1'][0]['assets'][0].pop('digest')
        with self.assertRaises(DeliveryError): self.source.candidate(self.current,self.root)

    def test_failed_ci_and_older_revision_do_not_download_image(self):
        self.metadata['/actions/runs/12']['conclusion']='failure'
        with self.assertRaises(DeliveryError): self.source.candidate(self.current,self.root)
        self.assertEqual(self.http.downloads,[1])
        self.metadata['/actions/runs/12']['conclusion']='success'
        self.metadata['/compare/'+'a'*40+'...'+self.sha]['status']='behind'
        with self.assertRaises(DeliveryError): self.source.candidate(self.current,self.root)
        self.assertNotIn(2,self.http.downloads)

    def test_redirect_strips_authorization_and_rejects_http(self):
        handler=SafeRedirect({'api.github.com','release-assets.githubusercontent.com'})
        request=urllib.request.Request('https://api.github.com/asset',headers={'Authorization':'Bearer synthetic'})
        redirected=handler.redirect_request(request,None,302,'',{},'https://release-assets.githubusercontent.com/file')
        self.assertIsNone(redirected.get_header('Authorization'))
        with self.assertRaises(DeliveryError):
            handler.redirect_request(request,None,302,'',{},'http://release-assets.githubusercontent.com/file')
