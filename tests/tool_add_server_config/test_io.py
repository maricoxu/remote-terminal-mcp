import unittest
import tempfile
import os
from config_manager.io import ConfigIO


class TestConfigIO(unittest.TestCase):
    def setUp(self):
        self.tempfile = tempfile.NamedTemporaryFile(delete=False)
        self.config_path = self.tempfile.name
        self.io = ConfigIO(self.config_path)

    def tearDown(self):
        os.unlink(self.config_path)

    def test_save_and_load_config(self):
        data = {'servers': {'test': {'host': '1.2.3.4', 'username': 'root', 'port': 22}}}
        self.io.save_config(data, merge=False)
        loaded = self.io.load_config()
        self.assertEqual(loaded['servers']['test']['host'], '1.2.3.4')

if __name__ == '__main__':
    unittest.main()
