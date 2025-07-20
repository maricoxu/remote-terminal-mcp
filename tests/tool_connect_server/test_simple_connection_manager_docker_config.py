#!/usr/bin/env python3
"""
SimpleConnectionManager Docker配置读取测试
测试修复的bug：确保能正确读取docker_config字段
"""

import os
import sys
import tempfile
import unittest
import yaml
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from python.connect import SimpleConnectionManager, ServerConfig, ConnectionType


class TestSimpleConnectionManagerDockerConfig(unittest.TestCase):
    """SimpleConnectionManager Docker配置读取测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.yaml")
        
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_docker_config_field(self):
        """测试读取docker_config字段（修复的bug）"""
        # 创建使用docker_config字段的配置
        test_config = {
            "servers": {
                "test_server": {
                    "host": "test.example.com",
                    "username": "testuser",
                    "connection_type": "relay",
                    "docker_config": {
                        "container_name": "test_container",
                        "shell": "zsh"
                    }
                }
            }
        }
        
        # 写入配置文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        
        # 创建SimpleConnectionManager并加载配置
        cm = SimpleConnectionManager(self.config_path)
        server_config = cm.servers.get("test_server")
        
        # 验证配置正确读取
        self.assertIsNotNone(server_config)
        self.assertEqual(server_config.docker_container, "test_container")
        self.assertEqual(server_config.docker_shell, "zsh")
        self.assertEqual(server_config.connection_type, ConnectionType.RELAY)
    
    def test_load_specs_docker_field(self):
        """测试读取specs.docker字段"""
        # 创建使用specs.docker字段的配置
        test_config = {
            "servers": {
                "test_server": {
                    "host": "test.example.com",
                    "username": "testuser",
                    "connection_type": "ssh",
                    "specs": {
                        "docker": {
                            "container_name": "specs_container",
                            "shell": "bash"
                        }
                    }
                }
            }
        }
        
        # 写入配置文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        
        # 创建SimpleConnectionManager并加载配置
        cm = SimpleConnectionManager(self.config_path)
        server_config = cm.servers.get("test_server")
        
        # 验证配置正确读取
        self.assertIsNotNone(server_config)
        self.assertEqual(server_config.docker_container, "specs_container")
        self.assertEqual(server_config.docker_shell, "bash")
        self.assertEqual(server_config.connection_type, ConnectionType.SSH)
    
    def test_load_docker_field(self):
        """测试读取docker字段"""
        # 创建使用docker字段的配置
        test_config = {
            "servers": {
                "test_server": {
                    "host": "test.example.com",
                    "username": "testuser",
                    "connection_type": "relay",
                    "docker": {
                        "container_name": "docker_container",
                        "shell": "zsh"
                    }
                }
            }
        }
        
        # 写入配置文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        
        # 创建SimpleConnectionManager并加载配置
        cm = SimpleConnectionManager(self.config_path)
        server_config = cm.servers.get("test_server")
        
        # 验证配置正确读取
        self.assertIsNotNone(server_config)
        self.assertEqual(server_config.docker_container, "docker_container")
        self.assertEqual(server_config.docker_shell, "zsh")
    
    def test_docker_config_priority(self):
        """测试Docker配置优先级：specs.docker > docker > docker_config"""
        # 创建包含多种Docker配置的配置（应该优先使用specs.docker）
        test_config = {
            "servers": {
                "test_server": {
                    "host": "test.example.com",
                    "username": "testuser",
                    "connection_type": "ssh",
                    "specs": {
                        "docker": {
                            "container_name": "specs_container",
                            "shell": "bash"
                        }
                    },
                    "docker": {
                        "container_name": "docker_container",
                        "shell": "zsh"
                    },
                    "docker_config": {
                        "container_name": "docker_config_container",
                        "shell": "fish"
                    }
                }
            }
        }
        
        # 写入配置文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        
        # 创建SimpleConnectionManager并加载配置
        cm = SimpleConnectionManager(self.config_path)
        server_config = cm.servers.get("test_server")
        
        # 验证优先级：specs.docker应该优先
        self.assertIsNotNone(server_config)
        self.assertEqual(server_config.docker_container, "specs_container")
        self.assertEqual(server_config.docker_shell, "bash")
    
    def test_no_docker_config(self):
        """测试没有Docker配置的情况"""
        # 创建没有Docker配置的配置
        test_config = {
            "servers": {
                "test_server": {
                    "host": "test.example.com",
                    "username": "testuser",
                    "connection_type": "ssh"
                }
            }
        }
        
        # 写入配置文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        
        # 创建SimpleConnectionManager并加载配置
        cm = SimpleConnectionManager(self.config_path)
        server_config = cm.servers.get("test_server")
        
        # 验证没有Docker配置时返回None
        self.assertIsNotNone(server_config)
        self.assertIsNone(server_config.docker_container)
        self.assertEqual(server_config.docker_shell, "zsh")  # 默认值
    
    def test_empty_docker_config(self):
        """测试空的Docker配置"""
        # 创建空的Docker配置
        test_config = {
            "servers": {
                "test_server": {
                    "host": "test.example.com",
                    "username": "testuser",
                    "connection_type": "relay",
                    "docker_config": {}
                }
            }
        }
        
        # 写入配置文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        
        # 创建SimpleConnectionManager并加载配置
        cm = SimpleConnectionManager(self.config_path)
        server_config = cm.servers.get("test_server")
        
        # 验证空配置时返回None
        self.assertIsNotNone(server_config)
        self.assertIsNone(server_config.docker_container)
    
    def test_tj11_like_config(self):
        """测试类似tj11的配置（实际场景）"""
        # 创建类似tj11的配置
        test_config = {
            "servers": {
                "tj11": {
                    "host": "tjdm-isa-ai-p800node11.tjdm",
                    "username": "xuyehua",
                    "connection_type": "relay",
                    "docker_config": {
                        "container_name": "xyh_pytorch",
                        "shell": "zsh"
                    }
                }
            }
        }
        
        # 写入配置文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f, default_flow_style=False, allow_unicode=True)
        
        # 创建SimpleConnectionManager并加载配置
        cm = SimpleConnectionManager(self.config_path)
        server_config = cm.servers.get("tj11")
        
        # 验证配置正确读取（这是修复的bug的核心测试）
        self.assertIsNotNone(server_config)
        self.assertEqual(server_config.docker_container, "xyh_pytorch")
        self.assertEqual(server_config.docker_shell, "zsh")
        self.assertEqual(server_config.connection_type, ConnectionType.RELAY)
        self.assertEqual(server_config.host, "tjdm-isa-ai-p800node11.tjdm")
        self.assertEqual(server_config.username, "xuyehua")


if __name__ == "__main__":
    unittest.main() 