"""Opt-in GnuPG round trip with synthetic disposable external recovery keys."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backup import encrypted_backup


@unittest.skipUnless(os.environ.get('LARA_CRYPTO_INTEGRATION')=='1','opt-in local GnuPG integration')
class CryptoIntegrationTest(unittest.TestCase):
    """Encrypt with public-only storage and decrypt using a separate recovery keyring."""
    def test_external_key_restores_exact_snapshot_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            external=root/'external'; public=root/'public'; scratch=root/'scratch'
            for folder in (external,public,scratch): folder.mkdir(mode=0o700)
            def gpg(home,*args,data=None):
                return subprocess.run(['/usr/bin/gpg','--homedir',str(home),'--batch','--pinentry-mode','loopback',*args],
                                      input=data,capture_output=True,check=True).stdout
            try:
                gpg(external,'--passphrase','','--quick-generate-key','N02 Synthetic Recovery','rsa2048','encr','0')
                listing=gpg(external,'--with-colons','--list-keys').decode()
                fingerprint=next(line.split(':')[9] for line in listing.splitlines() if line.startswith('fpr:'))
                gpg(public,'--import',data=gpg(external,'--export',fingerprint))
                self.assertNotIn(b'sec:',gpg(public,'--with-colons','--list-secret-keys'))
                class Storage:
                    def upload(self,path,app,revision,created):
                        shutil.copyfile(path,root/'downloaded.gpg')
                        return {'id':'synthetic','app':app,'revision':revision,'verified':True}
                settings={'scratch_dir':str(scratch),'public_keyring':str(public),
                          'recipient_fingerprint':fingerprint,'expiry_enabled':False}
                expected=b'N02 synthetic archive recovery bytes'
                encrypted_backup(lambda path:path.write_bytes(expected),'notey',{'revision':'a'*40},settings,Storage())
                self.assertNotIn(expected,(root/'downloaded.gpg').read_bytes())
                actual=gpg(external,'--passphrase','','--decrypt',str(root/'downloaded.gpg'))
                self.assertEqual(actual,expected)
                self.assertEqual(list(scratch.iterdir()),[])
            finally:
                for home in (external,public):
                    subprocess.run(['/usr/bin/gpgconf','--homedir',str(home),'--kill','gpg-agent'],capture_output=True)
