import unittest
from unittest.mock import patch
from config_manager.interaction import UserInteraction
from config_manager.server_info import ServerInfoCollector

class TestServerInfoCollector(unittest.TestCase):
    def setUp(self):
        self.ia = UserInteraction(force_interactive=True, auto_mode=True)
        self.collector = ServerInfoCollector(self.ia)

    def test_parse_user_host(self):
        self.assertEqual(self.collector.parse_user_host("root@1.2.3.4"), ("root", "1.2.3.4"))
        self.assertIsNone(self.collector.parse_user_host("badformat"))

    def test_validate_port(self):
        self.assertTrue(self.collector.validate_port("22"))
        self.assertFalse(self.collector.validate_port("70000"))

    def test_get_user_host_with_mock(self):
        # patch smart_input 直接返回合法格式
        with patch.object(self.ia, 'smart_input', return_value='testuser@auto.test.com'):
            user, host = self.collector.get_user_host({})
            self.assertEqual(user, 'testuser')
            self.assertEqual(host, 'auto.test.com')

if __name__ == '__main__':
    unittest.main()
