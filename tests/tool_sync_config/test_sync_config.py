import unittest
from config_manager.interaction import UserInteraction
from config_manager.sync_config import SyncConfigCollector

class TestSyncConfigCollector(unittest.TestCase):
    def setUp(self):
        self.ia = UserInteraction(force_interactive=True, auto_mode=True)
        self.sync = SyncConfigCollector(self.ia)

    def test_configure_sync_skip(self):
        # 不启用同步
        result = self.sync.configure_sync({'enabled': False})
        self.assertEqual(result, {})

if __name__ == '__main__':
    unittest.main()
