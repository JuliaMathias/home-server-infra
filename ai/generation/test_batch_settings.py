"""Check bounded reasoning controls without inference or live services."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('batch',Path(__file__).with_name('run-batch.py'))
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


class ReasoningSettingsTests(unittest.TestCase):
    """Defaults and invalid budgets must not silently enable unbounded thinking."""

    def test_off_forces_zero_allowance(self):
        """An off runtime keeps its original behavior regardless of unused budget."""
        self.assertEqual(batch.runtime_reasoning_settings('off',256),
                         {'GENERATION_REASONING':'off','GENERATION_REASONING_BUDGET':'0'})

    def test_on_records_explicit_bound(self):
        """Enabled experiments pass the requested cap to runtime configuration."""
        self.assertEqual(batch.runtime_reasoning_settings('on',256),
                         {'GENERATION_REASONING':'on','GENERATION_REASONING_BUDGET':'256'})

    def test_invalid_budgets_fail(self):
        """Negative, excessive and noninteger allowances fail before model work."""
        for value in [-1,2049,True,1.5,'256']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):batch.runtime_reasoning_settings('on',value)

    def test_invalid_mode_fails(self):
        """Unsupported modes cannot silently pick runtime defaults."""
        with self.assertRaises(ValueError):batch.runtime_reasoning_settings('auto',256)


if __name__ == '__main__':unittest.main()
