"""Interactive desktop OAuth setup with PKCE; never print codes or credentials.

Execute a reviewed copy on the Mac. The user creates the Desktop OAuth client
in Google Cloud and approves the browser consent. No Google service is created
by this program; it creates only the explicitly named private backup folder.
"""
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import json
import os
from pathlib import Path
import secrets
import time
import urllib.parse
import webbrowser

from common import HTTP, private_text
from drive import DRIVE_SCOPE


def authorize(client_file, destination, folder_name):
    """Obtain dedicated drive.file offline access and save a private credential."""
    destination=Path(destination)
    if destination.exists():
        raise ValueError('Refusing to overwrite an existing credential')
    client=json.loads(private_text(client_file))['installed']
    state=secrets.token_urlsafe(32)
    verifier=secrets.token_urlsafe(64)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    result={}
    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed=urllib.parse.urlsplit(self.path)
            fields=urllib.parse.parse_qs(parsed.query)
            valid=(parsed.path=='/oauth2/callback' and hmac.compare_digest(fields.get('state',[''])[0],state))
            if not valid:
                self.send_response(400); self.end_headers(); return
            result['code']=fields.get('code',[''])[0]
            self.send_response(200); self.end_headers()
            self.wfile.write(b'Authorization received. Return to the terminal.')
        def log_message(self,*args):
            pass  # Callback URLs include an authorization code.
    with HTTPServer(('127.0.0.1',0),Callback) as server:
        server.timeout=1
        redirect='http://127.0.0.1:%d/oauth2/callback' % server.server_port
        url='https://accounts.google.com/o/oauth2/v2/auth?'+urllib.parse.urlencode({
            'client_id':client['client_id'],'redirect_uri':redirect,'response_type':'code',
            'scope':DRIVE_SCOPE,'access_type':'offline','prompt':'consent','state':state,
            'code_challenge':challenge,'code_challenge_method':'S256'})
        if not webbrowser.open(url):
            raise RuntimeError('Open a browser on this desktop before authorizing')
        deadline=time.monotonic()+180
        while 'code' not in result and time.monotonic()<deadline:
            server.handle_request()
    if not result.get('code'):
        raise RuntimeError('Browser consent did not complete')
    http=HTTP({'oauth2.googleapis.com','www.googleapis.com'})
    token=http.json('https://oauth2.googleapis.com/token',method='POST',
        headers={'Content-Type':'application/x-www-form-urlencoded'},
        data=urllib.parse.urlencode({'client_id':client['client_id'],
            'client_secret':client.get('client_secret',''),'redirect_uri':redirect,
            'grant_type':'authorization_code','code':result['code'],'code_verifier':verifier}).encode())
    if set(token.get('scope','').split())!={DRIVE_SCOPE} or not token.get('refresh_token'):
        raise RuntimeError('Dedicated offline Drive authorization was not granted')
    headers={'Authorization':'Bearer '+token['access_token'],'Content-Type':'application/json'}
    folder=http.json('https://www.googleapis.com/drive/v3/files?fields=id',method='POST',headers=headers,
                    data=json.dumps({'name':folder_name,'mimeType':'application/vnd.google-apps.folder'}).encode())
    credential={'client_id':client['client_id'],'client_secret':client.get('client_secret',''),
                'refresh_token':token['refresh_token'],'folder_id':folder['id']}
    descriptor=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'w') as stream:
        json.dump(credential,stream)
    print('Dedicated Drive authorization saved to the private output file.')


def main():
    """Run only when the user explicitly starts account authorization."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('client_file'); parser.add_argument('destination'); parser.add_argument('folder_name')
    args=parser.parse_args()
    try:
        authorize(args.client_file,args.destination,args.folder_name)
        return 0
    except Exception:
        print('Drive authorization failed; no credential values are shown.')
        return 1


if __name__=='__main__':
    raise SystemExit(main())
