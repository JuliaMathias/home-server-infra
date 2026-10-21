"""Check device placement and GPU preconditions without inference or live services."""
import json
from pathlib import Path
import tempfile
import unittest

import runtime_session


def fake_inspect(running):
    """Return a docker-inspect stand-in reporting a fixed container state."""
    def inspect(name):
        if running is None:
            return 1, '', 'Error: No such object: ' + name
        return 0, json.dumps([{'State': {'Running': running}}]), ''
    return inspect


class DeviceSettingsTests(unittest.TestCase):
    """Defaults keep CPU-only behavior; GPU placement must be explicit and bounded."""

    def setUp(self):
        """Provide image pin files in a temporary stand-in for the service directory."""
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'runtime-image.txt').write_text('cpu-image@sha256:aa\n')
        (self.root / 'runtime-image-cuda.txt').write_text('cuda-image@sha256:bb\n')

    def tearDown(self):
        """Remove temporary pin files."""
        self.tmp.cleanup()

    def test_zero_layers_keeps_cpu_image_without_gpu_override(self):
        """The default path uses the original image and no GPU Compose override."""
        settings = runtime_session.device_settings('0', 16, self.root)
        self.assertEqual(settings['device'], 'cpu')
        self.assertEqual(settings['env']['GENERATION_IMAGE'], 'cpu-image@sha256:aa')
        self.assertNotIn(str(self.root / 'compose.gpu.yaml'), settings['compose'])
        self.assertEqual(settings['env']['GENERATION_MEMORY_LIMIT'], '16g')

    def test_auto_and_counts_select_cuda_image_and_override(self):
        """GPU placement switches image and adds the override, preserving the request."""
        for layers in ['auto', 20, '33']:
            with self.subTest(layers=layers):
                settings = runtime_session.device_settings(layers, 24, self.root)
                self.assertEqual(settings['device'], 'gpu')
                self.assertEqual(settings['env']['GENERATION_IMAGE'], 'cuda-image@sha256:bb')
                self.assertIn(str(self.root / 'compose.gpu.yaml'), settings['compose'])
                self.assertEqual(settings['env']['GENERATION_GPU_LAYERS'], str(layers))

    def test_invalid_layers_fail_before_container_work(self):
        """Negative, oversized, boolean and free-form values are rejected."""
        for layers in [-1, 201, '201', True, 'all', '', 1.5]:
            with self.subTest(layers=layers):
                with self.assertRaises(ValueError):
                    runtime_session.device_settings(layers, 16, self.root)

    def test_invalid_memory_caps_fail(self):
        """The host-RAM cap must stay a bounded integer below installed memory."""
        for memory in [3, 29, 16.0, '16', True]:
            with self.subTest(memory=memory):
                with self.assertRaises(ValueError):
                    runtime_session.device_settings('0', memory, self.root)


class GpuPreconditionTests(unittest.TestCase):
    """GPU runs must not contend with Whisper for the 4 GB card."""

    def test_running_transcription_blocks_gpu_run(self):
        """A running transcription container stops the run before any model load."""
        with self.assertRaises(RuntimeError):
            runtime_session.ensure_gpu_available(fake_inspect(True))

    def test_stopped_or_missing_transcription_allows_gpu_run(self):
        """Stopped and absent transcription containers both leave the GPU free."""
        for state in [False, None]:
            with self.subTest(state=state):
                runtime_session.ensure_gpu_available(fake_inspect(state))

    def test_inspect_errors_are_not_treated_as_stopped(self):
        """An unexpected Docker error fails closed instead of assuming a free GPU."""
        with self.assertRaises(RuntimeError):
            runtime_session.ensure_gpu_available(lambda name: (1, '', 'permission denied'))


if __name__ == '__main__':
    unittest.main()
