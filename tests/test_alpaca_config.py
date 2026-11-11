import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import configure_alpaca
import server


class AlpacaConfigTests(unittest.TestCase):
    def test_save_and_read_with_environment_override(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config_path = root / '.alpaca-config.json'
            with patch.object(configure_alpaca, 'ROOT', root), patch.object(configure_alpaca, 'CONFIG_PATH', config_path), patch.object(server, 'ROOT', root), patch.dict(os.environ, {}, clear=True):
                configure_alpaca.save_config('paper-key', 'paper-secret')
                self.assertEqual(stat.S_IMODE(config_path.stat().st_mode), 0o600)
                self.assertEqual(server.alpaca_setting('ALPACA_API_SECRET'), 'paper-secret')
                self.assertEqual(server.alpaca_setting('ALPACA_ENV'), 'paper')
                with patch.dict(os.environ, {'ALPACA_API_KEY': 'override'}):
                    self.assertEqual(server.alpaca_setting('ALPACA_API_KEY'), 'override')
                with self.assertRaises(ValueError):
                    configure_alpaca.save_config('new-key', '')
                self.assertEqual(json.loads(config_path.read_text())['ALPACA_API_KEY'], 'paper-key')

    def test_invalid_config_does_not_leak_contents(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / '.alpaca-config.json').write_text('sensitive-data')
            with patch.object(server, 'ROOT', root), patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(server.OptionsDataError) as error:
                    server.alpaca_setting('ALPACA_API_KEY')
                self.assertNotIn('sensitive-data', str(error.exception))


if __name__ == '__main__':
    unittest.main()
