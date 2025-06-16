#!/usr/bin/env python3
"""
MCP工具本地测试
测试MCP服务器的各种工具功能
"""

import sys
import unittest
from pathlib import Path

# 添加测试工具路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from test_helpers import BaseTestCase, create_test_server_config, create_test_docker_config

class TestMCPTools(BaseTestCase):
    """测试MCP工具功能"""
    
    def test_mcp_server_import(self):
        """测试MCP服务器模块导入"""
        try:
            import mcp_server
            # 检查关键函数是否存在
            self.assertTrue(hasattr(mcp_server, 'create_tools_list'), "MCP服务器应该有create_tools_list函数")
            self.assertTrue(hasattr(mcp_server, 'handle_request'), "MCP服务器应该有handle_request函数")
            self.assertTrue(True, "MCP服务器模块导入成功")
        except ImportError as e:
            self.fail(f"MCP服务器模块导入失败: {e}")
    
    def test_config_manager_tools(self):
        """测试配置管理工具"""
        from enhanced_config_manager import EnhancedConfigManager
        
        # 使用临时配置目录
        config_manager = EnhancedConfigManager()
        
        # 测试关键方法存在
        critical_methods = [
            'quick_setup',
            'guided_setup', 
            'get_existing_servers',
            'preview_docker_wizard_command'
        ]
        
        for method_name in critical_methods:
            self.assert_method_exists(config_manager, method_name)
    
    def test_docker_config_tools(self):
        """测试Docker配置工具"""
        from docker_config_manager import DockerConfigManager
        
        docker_manager = DockerConfigManager()
        
        # 测试关键方法存在
        critical_methods = [
            'create_from_template',
            'create_default_templates'
        ]
        
        for method_name in critical_methods:
            self.assert_method_exists(docker_manager, method_name)
    
    def test_server_config_creation(self):
        """测试服务器配置创建"""
        from enhanced_config_manager import EnhancedConfigManager
        
        config_manager = EnhancedConfigManager()
        
        # 创建测试配置
        test_config = {
            'name': 'test-server',
            'host': '192.168.1.100',
            'username': 'testuser',
            'port': 22,
            'connection_type': 'ssh'
        }
        
        try:
            # 测试获取现有服务器配置不抛出异常
            result = config_manager.get_existing_servers()
            self.assertIsNotNone(result, "获取服务器配置应该返回结果")
        except Exception as e:
            self.fail(f"获取服务器配置失败: {e}")
    
    def test_docker_command_generation(self):
        """测试Docker命令生成"""
        from enhanced_config_manager import EnhancedConfigManager
        
        config_manager = EnhancedConfigManager()
        test_config = create_test_docker_config()
        
        try:
            # 这个方法会打印Docker命令，我们只需要确保它不抛出异常
            config_manager.preview_docker_wizard_command(test_config)
            self.assertTrue(True, "Docker命令生成正常执行")
        except Exception as e:
            self.fail(f"Docker命令生成失败: {e}")
    
    def test_config_file_operations(self):
        """测试配置文件操作"""
        from enhanced_config_manager import EnhancedConfigManager
        
        config_manager = EnhancedConfigManager()
        
        # 测试配置文件路径
        config_path = config_manager.config_path
        self.assertTrue(str(config_path).endswith('.remote-terminal/config.yaml'),
                       "配置文件路径应该使用.remote-terminal目录")
    
    def test_mcp_tool_availability(self):
        """测试MCP工具的可用性"""
        try:
            import mcp_server
            
            # 获取工具列表
            tools = mcp_server.create_tools_list()
            
            # 检查关键工具是否注册
            expected_tools = [
                'list_servers',
                'connect_server', 
                'execute_command',
                'interactive_config_wizard'
            ]
            
            tool_names = [tool['name'] for tool in tools]
            
            for expected_tool in expected_tools:
                self.assertIn(expected_tool, tool_names, 
                             f"MCP工具列表应该包含{expected_tool}")
            
            self.assertTrue(True, "MCP工具可用性检查成功")
            
        except Exception as e:
            self.fail(f"MCP工具可用性检查失败: {e}")

class TestConfigurationConsistency(BaseTestCase):
    """测试配置一致性"""
    
    def test_config_directory_consistency(self):
        """测试配置目录一致性"""
        from enhanced_config_manager import EnhancedConfigManager
        from docker_config_manager import DockerConfigManager
        
        enhanced_manager = EnhancedConfigManager()
        docker_manager = DockerConfigManager()
        
        # 检查两个管理器使用相同的配置目录
        enhanced_config_dir = enhanced_manager.config_path.parent
        docker_config_dir = docker_manager.config_dir
        
        self.assertEqual(enhanced_config_dir.name, docker_config_dir.name,
                        "所有配置管理器应该使用相同的配置目录名称")
        
        # 确保都使用.remote-terminal目录
        self.assertEqual(enhanced_config_dir.name, '.remote-terminal',
                        "配置目录应该是.remote-terminal")
        self.assertEqual(docker_config_dir.name, '.remote-terminal',
                        "Docker配置目录应该是.remote-terminal")

if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2) 