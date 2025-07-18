import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../python')))
import builtins
from config_manager.interaction import UserInteraction
builtins.input = lambda *a, **k: "mocked"
UserInteraction.smart_input = lambda self, *a, **k: "mocked"
from unittest.mock import patch
import unittest

class TestUserInteraction(unittest.TestCase):
    def setUp(self):
        self.patcher_input = patch('builtins.input', return_value='mocked')
        self.patcher_smart = patch('config_manager.interaction.UserInteraction.smart_input', return_value='mocked')
        self.addCleanup(self.patcher_input.stop)
        self.addCleanup(self.patcher_smart.stop)
        self.mock_input = self.patcher_input.start()
        self.mock_smart = self.patcher_smart.start() 