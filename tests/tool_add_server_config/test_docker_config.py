import unittest
from unittest.mock import patch
from config_manager.interaction import UserInteraction

from config_manager.docker_config import DockerConfigCollector


class TestDockerConfigCollector(unittest.TestCase):
    def setUp(self):
        self.ia = UserInteraction(force_interactive=True, auto_mode=True)
        self.docker = DockerConfigCollector(self.ia)

    def test_configure_docker_skip(self):
        # Mock选择不使用Docker
        with patch.object(self.ia, 'smart_input', side_effect=['4']):  # 选择4: 不使用Docker
            result = self.docker.configure_docker({'enabled': False})
            self.assertEqual(result, {})

if __name__ == '__main__':
    unittest.main()
