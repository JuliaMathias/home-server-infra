"""Behavioral checks for explicit candidate selection and offline atomic downloads."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from candidate_config import candidate_settings

ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location('downloader', ROOT / 'download-model.py')
downloader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(downloader)


class CandidateTests(unittest.TestCase):
    """Use synthetic bytes and temporary directories; never contact model hosts."""

    def setUp(self):
        """Create a minimal immutable metadata fixture and isolated storage."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = b'synthetic test weight bytes'
        self.candidate = {'repository':'test/model', 'revision':'a'*40,
                          'filename':'model.gguf', 'bytes':len(self.payload),
                          'sha256':hashlib.sha256(self.payload).hexdigest()}
        self.path = self.root / 'candidate.json'
        self.write_candidate()

    def write_candidate(self):
        """Persist the current synthetic metadata for a test invocation."""
        self.path.write_text(json.dumps(self.candidate))

    def download(self, payload=None):
        """Run the real download entry point with a fake response and test argv."""
        with patch('sys.argv', ['download-model.py','--candidate',str(self.path)]), \
             patch.dict(os.environ, {'MODEL_DEST':str(self.root/'weights')}), \
             patch.object(downloader.urllib.request, 'urlopen', return_value=io.BytesIO(self.payload if payload is None else payload)) as network:
            downloader.main()
        return network

    def test_original_metadata_retains_paths(self):
        """Adding candidate selection must retain the original default location."""
        _, host, container, alias = candidate_settings(self.path, self.root)
        self.assertEqual(host, self.root/'qwen3-14b')
        self.assertEqual(container, '/models/qwen3-14b/model.gguf')
        self.assertEqual(alias, 'qwen3-14b-trial')

    def test_explicit_candidate_uses_separate_paths(self):
        """An alternative must not reuse the original model directory or alias."""
        self.candidate.update(model_directory='alternative', alias='alternative-trial')
        self.write_candidate()
        _, host, container, alias = candidate_settings(self.path, self.root)
        self.assertEqual(host, self.root/'alternative')
        self.assertEqual(container, '/models/alternative/model.gguf')
        self.assertEqual(alias, 'alternative-trial')

    def test_rejects_traversal_and_unpinned_identity(self):
        """Bad components and mutable identities fail before download or file writes."""
        baseline = self.candidate.copy()
        for field, value in [('model_directory','../escape'),('filename','/tmp/escape'),
                             ('model_directory','..'),('repository','https://host/model'),
                             ('revision','main'),('sha256','wrong'),('bytes',True),
                             ('bytes',0),('alias','name\ncommand')]:
            with self.subTest(field=field, value=value):
                self.candidate = dict(baseline, **{field:value})
                self.write_candidate()
                with self.assertRaises(ValueError): candidate_settings(self.path, self.root)

    def test_valid_download_is_atomic_and_records_manifest(self):
        """Only verified bytes become the final model, with exact provenance."""
        network = self.download()
        folder = self.root/'weights'
        self.assertEqual((folder/'model.gguf').read_bytes(), self.payload)
        self.assertFalse((folder/'model.gguf.partial').exists())
        self.assertEqual(json.loads((folder/'source-manifest.json').read_text()), self.candidate)
        self.assertIn('/resolve/'+'a'*40+'/', network.call_args.args[0])

    def test_corrupt_download_preserves_partial_without_final(self):
        """Failed integrity checks preserve evidence and never publish bad weights."""
        with self.assertRaises(RuntimeError): self.download(b'corrupt')
        folder = self.root/'weights'
        self.assertFalse((folder/'model.gguf').exists())
        self.assertEqual((folder/'model.gguf.partial').read_bytes(), b'corrupt')
        self.assertFalse((folder/'source-manifest.json').exists())

    def test_existing_mismatch_is_not_overwritten(self):
        """Existing mismatched assets survive and no network call occurs."""
        folder = self.root/'weights';folder.mkdir()
        (folder/'model.gguf').write_bytes(b'preserve me')
        with patch('sys.argv',['download-model.py','--candidate',str(self.path)]), \
             patch.dict(os.environ, {'MODEL_DEST':str(folder)}), \
             patch.object(downloader.urllib.request,'urlopen') as network:
            with self.assertRaises(RuntimeError): downloader.main()
            network.assert_not_called()
        self.assertEqual((folder/'model.gguf').read_bytes(), b'preserve me')

    def test_existing_valid_model_does_not_download_again(self):
        """A verified existing asset is reused without duplicate network work."""
        self.download()
        with patch('sys.argv',['download-model.py','--candidate',str(self.path)]), \
             patch.dict(os.environ, {'MODEL_DEST':str(self.root/'weights')}), \
             patch.object(downloader.urllib.request,'urlopen') as network:
            downloader.main();network.assert_not_called()

    def test_foreign_manifest_is_preserved(self):
        """Selecting another model cannot overwrite a directory's provenance."""
        folder = self.root/'weights';folder.mkdir()
        manifest = dict(self.candidate, repository='other/model')
        (folder/'source-manifest.json').write_text(json.dumps(manifest))
        with patch('sys.argv',['download-model.py','--candidate',str(self.path)]), \
             patch.dict(os.environ, {'MODEL_DEST':str(folder)}), \
             patch.object(downloader.urllib.request,'urlopen') as network:
            with self.assertRaises(RuntimeError): downloader.main()
            network.assert_not_called()
        self.assertEqual(json.loads((folder/'source-manifest.json').read_text()),manifest)
        self.assertFalse((folder/'model.gguf').exists())

    def test_valid_existing_file_repairs_missing_manifest(self):
        """A verified asset can recover provenance after an interrupted final write."""
        folder = self.root/'weights';folder.mkdir()
        (folder/'model.gguf').write_bytes(self.payload)
        with patch('sys.argv',['download-model.py','--candidate',str(self.path)]), \
             patch.dict(os.environ, {'MODEL_DEST':str(folder)}), \
             patch.object(downloader.urllib.request,'urlopen') as network:
            downloader.main();network.assert_not_called()
        self.assertEqual(json.loads((folder/'source-manifest.json').read_text()),self.candidate)


if __name__ == '__main__':
    unittest.main()
