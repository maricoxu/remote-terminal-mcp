import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../python')))
from config_manager.interaction import UserInteraction
from config_manager.server_info import ServerInfoCollector 
from unittest.mock import patch

import unittest

class TestServerInfoCollector(unittest.TestCase):
    def setUp(self):
        self.patcher_input = patch('builtins.input', return_value='testuser@auto.test.com')
        self.patcher_smart = patch('config_manager.interaction.UserInteraction.smart_input', return_value='testuser@auto.test.com')
        self.addCleanup(self.patcher_input.stop)
        self.addCleanup(self.patcher_smart.stop)
        self.mock_input = self.patcher_input.start()
        self.mock_smart = self.patcher_smart.start()
        self.ia = UserInteraction(force_interactive=True, auto_mode=True)
        self.collector = ServerInfoCollector(self.ia) 