"""Dedicated desktop authorization checks with fake browser, callback and Google."""
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.parse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from authorize_drive import authorize
from drive import DRIVE_SCOPE

class AuthorizeTest(unittest.TestCase):
    """Keep credentials private and require the exact consent/PKCE scope."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.client=self.root/'client.json'
        self.client.write_text(json.dumps({'installed':{'client_id':'synthetic','client_secret':'synthetic'}}))
        self.client.chmod(0o600)
        self.destination=self.root/'drive.json'
        self.scope=DRIVE_SCOPE; self.state_valid=True; self.calls=[]; self.query={}
        outer=self
        class Server:
            def __init__(self,address,handler):
                outer.assertEqual(address[0],'127.0.0.1')
                self.handler=handler; self.server_port=12345
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def handle_request(self):
                request=object.__new__(self.handler)
                state=outer.query['state'][0] if outer.state_valid else 'wrong-state'
                request.path='/oauth2/callback?'+urllib.parse.urlencode({'state':state,'code':'synthetic-code'})
                request.send_response=lambda status:None
                request.end_headers=lambda:None
                request.wfile=io.BytesIO()
                request.do_GET()
        class HTTP:
            def __init__(self,hosts): pass
            def json(self,url,**kwargs):
                outer.calls.append((url,kwargs))
                if url.endswith('/token'):
                    fields=urllib.parse.parse_qs(kwargs['data'].decode())
                    challenge=base64.urlsafe_b64encode(hashlib.sha256(fields['code_verifier'][0].encode()).digest()).rstrip(b'=').decode()
                    outer.assertEqual(challenge,outer.query['code_challenge'][0])
                    return {'scope':outer.scope,'refresh_token':'synthetic-refresh','access_token':'synthetic-access'}
                return {'id':'private-folder'}
        def browser(url):
            self.query=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            self.assertEqual(self.query['scope'],[DRIVE_SCOPE])
            self.assertEqual(self.query['code_challenge_method'],['S256'])
            return True
        for name,value in [('HTTPServer',Server),('HTTP',HTTP),('webbrowser.open',browser)]:
            self.addCleanup(patch.stopall)
            patch('authorize_drive.'+name,value).start()

    def test_exact_scope_and_pkce_write_only_new_private_credentials(self):
        authorize(self.client,self.destination,'Notey synthetic backup folder')
        self.assertEqual(self.destination.stat().st_mode & 0o777,0o600)
        self.assertEqual(json.loads(self.destination.read_text())['folder_id'],'private-folder')
        self.assertEqual(len(self.calls),2)
        with self.assertRaises(ValueError): authorize(self.client,self.destination,'Do not overwrite')
        self.assertEqual(len(self.calls),2)

    def test_broader_scope_does_not_create_folder_or_save_credentials(self):
        self.scope='https://www.googleapis.com/auth/drive'
        with self.assertRaises(RuntimeError): authorize(self.client,self.destination,'Rejected')
        self.assertEqual(len(self.calls),1)
        self.assertFalse(self.destination.exists())

    def test_wrong_callback_state_cannot_exchange_a_code(self):
        self.state_valid=False
        with patch('authorize_drive.time.monotonic',side_effect=[0,0,181]):
            with self.assertRaises(RuntimeError): authorize(self.client,self.destination,'Rejected')
        self.assertEqual(self.calls,[])
        self.assertFalse(self.destination.exists())
