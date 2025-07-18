import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../python')))
from config_manager.io import ConfigIO
import unittest

class TestConfigIO(unittest.TestCase):
    def test_dummy(self):
        self.assertTrue(True)
