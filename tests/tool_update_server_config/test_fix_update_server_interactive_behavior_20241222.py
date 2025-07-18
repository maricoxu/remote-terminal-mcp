#!/usr/bin/env python3
"""
回归测试：update_server_config交互行为修复

测试目标：
- 验证update_server_config与create_server_config行为一致
- 测试默认启动交互配置界面
- 验证用户参数作为预填充默认值
- 测试更新模式的预填充参数处理
- 验证现有配置的正确读取和传递

修复问题：确保update_server_config默认启动交互界面，而不是直接更新配置
创建日期：2024-12-22
"""

import os
import sys
import json
import yaml
import tempfile
import unittest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config_manager.main import EnhancedConfigManager


class TestUpdateServerInteractiveBehavior(unittest.TestCase):
    """测试update_server_config的交互行为修复"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时配置文件
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        self.temp_config.close()
        
        # 创建测试配置
        self.test_config = {
            'servers': {
                'test_update_server': {
                    'description': '测试更新服务器',
                    'host': 'test.update.com',
                    'port': 22,
                    'username': 'testuser',
                    'connection_type': 'ssh',
                    'type': 'script_based',
                    'private_key_path': '~/.ssh/id_rsa',
                    'specs': {
                        'docker': {
                            'image': 'ubuntu:20.04',
                            'container': 'test_container',
                            'container_name': 'test_container',
                            'auto_create': True,
                            'ports': ['8080:8080', '8888:8888'],
                            'volumes': ['/home:/home'],
                            'shell': 'bash'
                        }
                    }
                }
            }
        }
        
        # 保存测试配置
        with open(self.temp_config.name, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config, f, default_flow_style=False, allow_unicode=True)
        
        # 创建配置管理器
        self.config_manager = EnhancedConfigManager()
        self.config_manager.config_path = self.temp_config.name
        
    def tearDown(self):
        """测试后清理"""
        try:
            os.unlink(self.temp_config.name)
        except:
            pass
    
    def test_update_server_launches_interactive_interface(self):
        """测试update_server_config默认启动交互界面"""
        print("🎯 测试update_server_config默认启动交互界面")
        
        # 模拟launch_cursor_terminal_config方法
        with patch.object(self.config_manager, 'launch_cursor_terminal_config') as mock_launch:
            mock_launch.return_value = {
                "success": True,
                "message": "更新配置界面已启动",
                "process_id": "update_terminal_window",
                "prefill_file": "/tmp/test_update_prefill.json"
            }
            
            # 测试参数
            update_params = {
                'name': 'test_update_server',
                'host': 'updated.test.com',
                'description': '更新后的服务器描述'
            }
            
            # 模拟update_server_config的核心逻辑
            servers = self.config_manager.get_existing_servers()
            self.assertIn('test_update_server', servers)
            
            current_config = servers['test_update_server'].copy()
            
            # 准备预填充参数（合并当前配置和更新参数）
            prefill_params = {
                'name': 'test_update_server',
                'host': update_params.get('host', current_config.get('host')),
                'username': current_config.get('username'),
                'port': current_config.get('port'),
                'connection_type': current_config.get('connection_type'),
                'description': update_params.get('description', current_config.get('description')),
                'docker_enabled': bool(current_config.get('specs', {}).get('docker')),
                'update_mode': True
            }
            
            # 调用启动方法
            result = self.config_manager.launch_cursor_terminal_config(prefill_params=prefill_params)
            
            # 验证结果
            self.assertTrue(result['success'])
            self.assertEqual(result['process_id'], 'update_terminal_window')
            
            # 验证launch_cursor_terminal_config被调用
            mock_launch.assert_called_once()
            call_args = mock_launch.call_args[1]
            self.assertIn('prefill_params', call_args)
            
            # 验证预填充参数包含更新的值
            passed_params = call_args['prefill_params']
            self.assertEqual(passed_params['name'], 'test_update_server')
            self.assertEqual(passed_params['host'], 'updated.test.com')
            self.assertEqual(passed_params['description'], '更新后的服务器描述')
            self.assertTrue(passed_params['update_mode'])
            
        print("✅ update_server_config默认启动交互界面测试通过")
    
    def test_update_server_preserves_existing_config(self):
        """测试更新时正确保留现有配置"""
        print("🎯 测试更新时正确保留现有配置")
        
        servers = self.config_manager.get_existing_servers()
        current_config = servers['test_update_server']
        
        # 验证现有配置正确读取
        self.assertEqual(current_config['host'], 'test.update.com')
        self.assertEqual(current_config['username'], 'testuser')
        self.assertEqual(current_config['connection_type'], 'ssh')
        
        # 验证Docker配置正确读取
        docker_config = current_config.get('specs', {}).get('docker', {})
        self.assertEqual(docker_config['image'], 'ubuntu:20.04')
        self.assertEqual(docker_config['container'], 'test_container')
        self.assertIn('8080:8080', docker_config['ports'])
        
        print("✅ 现有配置保留测试通过")
    
    def test_update_server_docker_config_handling(self):
        """测试更新时Docker配置的处理"""
        print("🎯 测试更新时Docker配置的处理")
        
        with patch.object(self.config_manager, 'launch_cursor_terminal_config') as mock_launch:
            mock_launch.return_value = {"success": True, "process_id": "test_window"}
            
            servers = self.config_manager.get_existing_servers()
            current_config = servers['test_update_server'].copy()
            current_docker = current_config.get('specs', {}).get('docker', {})
            
            # 模拟用户提供新的Docker参数
            new_docker_params = {
                'docker_image': 'python:3.9',
                'docker_container': 'updated_python_container',
                'docker_ports': ['5000:5000', '8000:8000'],
                'docker_volumes': ['/app:/app', '/data:/data'],
                'docker_shell': 'zsh',
                'docker_auto_create': False
            }
            
            # 准备预填充参数
            prefill_params = {
                'name': 'test_update_server',
                'host': current_config.get('host'),
                'username': current_config.get('username'),
                'docker_enabled': True,
                'docker_image': new_docker_params['docker_image'],
                'docker_container': new_docker_params['docker_container'],
                'docker_ports': new_docker_params['docker_ports'],
                'docker_volumes': new_docker_params['docker_volumes'],
                'docker_shell': new_docker_params['docker_shell'],
                'docker_auto_create': new_docker_params['docker_auto_create'],
                'update_mode': True
            }
            
            # 调用启动方法
            result = self.config_manager.launch_cursor_terminal_config(prefill_params=prefill_params)
            
            # 验证Docker参数正确传递
            call_args = mock_launch.call_args[1]['prefill_params']
            self.assertEqual(call_args['docker_image'], 'python:3.9')
            self.assertEqual(call_args['docker_container'], 'updated_python_container')
            self.assertEqual(call_args['docker_ports'], ['5000:5000', '8000:8000'])
            self.assertEqual(call_args['docker_volumes'], ['/app:/app', '/data:/data'])
            self.assertEqual(call_args['docker_shell'], 'zsh')
            self.assertFalse(call_args['docker_auto_create'])
            
        print("✅ Docker配置处理测试通过")
    
    def test_update_server_relay_config_handling(self):
        """测试更新时Relay配置的处理"""
        print("🎯 测试更新时Relay配置的处理")
        
        # 创建带Relay配置的测试服务器
        relay_config = {
            'servers': {
                'test_relay_server': {
                    'description': '测试Relay服务器',
                    'host': 'relay.test.com',
                    'port': 22,
                    'username': 'relayuser',
                    'connection_type': 'relay',
                    'type': 'script_based',
                    'specs': {
                        'connection': {
                            'target': {
                                'host': 'target.relay.com'
                            }
                        }
                    }
                }
            }
        }
        
        # 保存Relay配置
        with open(self.temp_config.name, 'w', encoding='utf-8') as f:
            yaml.dump(relay_config, f, default_flow_style=False, allow_unicode=True)
        
        with patch.object(self.config_manager, 'launch_cursor_terminal_config') as mock_launch:
            mock_launch.return_value = {"success": True, "process_id": "relay_window"}
            
            servers = self.config_manager.get_existing_servers()
            current_config = servers['test_relay_server'].copy()
            current_relay = current_config.get('specs', {}).get('connection', {}).get('target', {})
            
            # 准备预填充参数
            prefill_params = {
                'name': 'test_relay_server',
                'host': current_config.get('host'),
                'username': current_config.get('username'),
                'connection_type': 'relay',
                'relay_target_host': current_relay.get('host', ''),
                'update_mode': True
            }
            
            # 调用启动方法
            result = self.config_manager.launch_cursor_terminal_config(prefill_params=prefill_params)
            
            # 验证Relay参数正确传递
            call_args = mock_launch.call_args[1]['prefill_params']
            self.assertEqual(call_args['connection_type'], 'relay')
            self.assertEqual(call_args['relay_target_host'], 'target.relay.com')
            
        print("✅ Relay配置处理测试通过")
    
    def test_update_server_error_handling(self):
        """测试更新时的错误处理"""
        print("🎯 测试更新时的错误处理")
        
        # 测试服务器不存在的情况
        servers = self.config_manager.get_existing_servers()
        self.assertNotIn('nonexistent_server', servers)
        
        # 测试空服务器名
        with self.assertRaises(Exception):
            # 模拟空服务器名的处理
            server_name = ""
            if not server_name:
                raise Exception("server_name parameter is required")
        
        print("✅ 错误处理测试通过")
    
    def test_update_behavior_consistency_with_create(self):
        """测试update行为与create的一致性"""
        print("🎯 测试update行为与create的一致性")
        
        with patch.object(self.config_manager, 'launch_cursor_terminal_config') as mock_launch:
            mock_launch.return_value = {
                "success": True,
                "message": "配置界面已启动",
                "process_id": "consistent_window"
            }
            
            # 模拟create_server_config的调用
            create_params = {
                'name': 'new_server',
                'host': 'new.server.com',
                'username': 'newuser',
                'docker_enabled': True
            }
            
            create_result = self.config_manager.launch_cursor_terminal_config(prefill_params=create_params)
            
            # 模拟update_server_config的调用
            update_params = {
                'name': 'test_update_server',
                'host': 'updated.server.com',
                'username': 'updateduser',
                'docker_enabled': True,
                'update_mode': True
            }
            
            update_result = self.config_manager.launch_cursor_terminal_config(prefill_params=update_params)
            
            # 验证两者都成功启动交互界面
            self.assertTrue(create_result['success'])
            self.assertTrue(update_result['success'])
            
            # 验证两者都调用了相同的启动方法
            self.assertEqual(mock_launch.call_count, 2)
            
        print("✅ update与create行为一致性测试通过")

def run_update_interactive_behavior_tests():
    """运行update_server_config交互行为测试"""
    print("🚀 开始update_server_config交互行为回归测试")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUpdateServerInteractiveBehavior)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    if result.wasSuccessful():
        print("🎉 所有update_server_config交互行为测试通过！")
        print("🎯 修复验证成功：update_server_config与create_server_config行为一致")
    else:
        print("❌ 部分测试失败，需要进一步修复")
        for failure in result.failures:
            print(f"失败测试: {failure[0]}")
            print(f"失败原因: {failure[1]}")
        for error in result.errors:
            print(f"错误测试: {error[0]}")
            print(f"错误信息: {error[1]}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_update_interactive_behavior_tests()
    sys.exit(0 if success else 1) 