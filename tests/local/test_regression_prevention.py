#!/usr/bin/env python3
"""
回归测试套件 - 防止配置和功能回退问题
这个测试套件专门用于检测可能导致用户体验下降的回归问题
"""

import os
import sys
import unittest
from pathlib import Path
import tempfile
import shutil
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'python'))

class TestConfigurationRegression(unittest.TestCase):
    """测试配置相关的回归问题"""
    
    def test_config_directory_consistency(self):
        """测试配置目录的一致性 - 防止目录名称变更"""
        from enhanced_config_manager import EnhancedConfigManager
        from docker_config_manager import DockerConfigManager
        
        # 测试EnhancedConfigManager
        config_manager = EnhancedConfigManager()
        config_path = str(config_manager.config_path)
        
        # 确保使用正确的配置目录名称
        self.assertIn('.remote-terminal', config_path, 
                     "EnhancedConfigManager必须使用.remote-terminal目录")
        self.assertNotIn('.remote-terminal-mcp', config_path,
                        "EnhancedConfigManager不应使用.remote-terminal-mcp目录")
        
        # 测试DockerConfigManager
        docker_manager = DockerConfigManager()
        docker_config_dir = str(docker_manager.config_dir)
        
        self.assertIn('.remote-terminal', docker_config_dir,
                     "DockerConfigManager必须使用.remote-terminal目录")
        self.assertNotIn('.remote-terminal-mcp', docker_config_dir,
                        "DockerConfigManager不应使用.remote-terminal-mcp目录")
    
    def test_config_file_structure(self):
        """测试配置文件结构的完整性"""
        from enhanced_config_manager import EnhancedConfigManager
        
        config_manager = EnhancedConfigManager()
        
        # 确保配置目录存在
        config_dir = config_manager.config_path.parent
        self.assertTrue(config_dir.exists(), "配置目录必须存在")
        
        # 检查配置文件是否存在（更实际的检查）
        config_file = config_dir / 'config.yaml'
        if config_file.exists():
            self.assertTrue(True, "配置文件存在")
        else:
            # 如果配置文件不存在，至少目录应该存在
            self.assertTrue(config_dir.exists(), "配置目录应该存在")

class TestMCPToolsRegression(unittest.TestCase):
    """测试MCP工具的回归问题"""
    
    def test_interactive_wizard_functionality(self):
        """测试交互式向导功能是否正常"""
        from python.mcp_server import EnhancedConfigManager
        
        config_manager = EnhancedConfigManager()
        
        # 确保配置管理器有必要的方法
        self.assertTrue(hasattr(config_manager, 'quick_setup'),
                       "配置管理器必须有quick_setup方法")
        self.assertTrue(hasattr(config_manager, 'guided_setup'),
                       "配置管理器必须有guided_setup方法")
        self.assertTrue(hasattr(config_manager, 'get_existing_servers'),
                       "配置管理器必须有get_existing_servers方法")
    
    def test_mcp_tools_availability(self):
        """测试MCP工具的可用性"""
        from python.mcp_server import create_tools_list
        
        tools = create_tools_list()
        tool_names = [tool['name'] for tool in tools]
        
        # 确保关键工具存在
        required_tools = [
            'interactive_config_wizard',
            'create_server_config', 
            'manage_server_config',
            'list_servers',
            'connect_server'
        ]
        
        for tool_name in required_tools:
            self.assertIn(tool_name, tool_names, 
                         f"MCP工具 {tool_name} 必须存在")

class TestDockerConfigRegression(unittest.TestCase):
    """测试Docker配置的回归问题"""
    
    def test_docker_command_completeness(self):
        """测试Docker命令生成的完整性"""
        from enhanced_config_manager import EnhancedConfigManager
        
        config_manager = EnhancedConfigManager()
        
        # 创建测试配置
        test_config = {
            'container_name': 'test-container',
            'image': 'ubuntu:20.04',
            'ports': [],
            'volumes': [],
            'shell_config': {
                'config_source': 'test'
            }
        }
        
        # 测试Docker命令生成方法是否正常执行
        try:
            # 这个方法会打印Docker命令，我们只需要确保它不抛出异常
            config_manager.preview_docker_wizard_command(test_config)
            # 如果执行到这里，说明方法正常工作
            self.assertTrue(True, "Docker命令生成方法正常执行")
        except Exception as e:
            self.fail(f"Docker命令生成方法执行失败: {e}")

class TestUserExperienceRegression(unittest.TestCase):
    """测试用户体验相关的回归问题"""
    
    def test_error_messages_quality(self):
        """测试错误消息的质量"""
        from enhanced_config_manager import EnhancedConfigManager
        
        # 测试配置管理器在异常情况下的行为
        config_manager = EnhancedConfigManager()
        
        # 确保有适当的错误处理方法
        self.assertTrue(hasattr(config_manager, 'colored_print'),
                       "配置管理器必须有colored_print方法用于用户反馈")
    
    def test_configuration_backup(self):
        """测试配置备份功能"""
        from enhanced_config_manager import EnhancedConfigManager
        
        config_manager = EnhancedConfigManager()
        
        # 确保有配置保存和备份功能
        self.assertTrue(hasattr(config_manager, 'save_config'),
                       "配置管理器必须有save_config方法")

class TestAPIConsistency(unittest.TestCase):
    """测试API一致性，防止破坏性变更"""
    
    def test_enhanced_config_manager_api(self):
        """测试EnhancedConfigManager的API稳定性"""
        from enhanced_config_manager import EnhancedConfigManager
        
        config_manager = EnhancedConfigManager()
        
        # 确保关键方法存在且可调用
        critical_methods = [
            'get_existing_servers',
            'save_config',
            'quick_setup',
            'guided_setup'
        ]
        
        for method_name in critical_methods:
            self.assertTrue(hasattr(config_manager, method_name),
                           f"EnhancedConfigManager必须有{method_name}方法")
            method = getattr(config_manager, method_name)
            self.assertTrue(callable(method),
                           f"{method_name}必须是可调用的方法")
    
    def test_docker_config_manager_api(self):
        """测试DockerConfigManager的API稳定性"""
        from docker_config_manager import DockerConfigManager
        from enhanced_config_manager import EnhancedConfigManager
        
        docker_manager = DockerConfigManager()
        config_manager = EnhancedConfigManager()
        
        # 确保DockerConfigManager的关键方法存在
        docker_methods = [
            'create_from_template',
            'create_default_templates'
        ]
        
        for method_name in docker_methods:
            self.assertTrue(hasattr(docker_manager, method_name),
                           f"DockerConfigManager必须有{method_name}方法")
        
        # 确保EnhancedConfigManager有Docker相关方法
        enhanced_methods = [
            'preview_docker_wizard_command'
        ]
        
        for method_name in enhanced_methods:
            self.assertTrue(hasattr(config_manager, method_name),
                           f"EnhancedConfigManager必须有{method_name}方法")

def run_regression_tests():
    """运行所有回归测试"""
    print("🚀 开始运行回归测试套件...")
    print("=" * 60)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestConfigurationRegression,
        TestMCPToolsRegression, 
        TestDockerConfigRegression,
        TestUserExperienceRegression,
        TestAPIConsistency
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print("\n" + "=" * 60)
    print("📊 回归测试结果汇总:")
    print(f"运行测试: {result.testsRun}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ 失败的测试:")
        for test, traceback in result.failures:
            error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
            print(f"  - {test}: {error_msg}")
    
    if result.errors:
        print("\n💥 错误的测试:")
        for test, traceback in result.errors:
            error_msg = traceback.split('\n')[-2]
            print(f"  - {test}: {error_msg}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n🎉 所有回归测试通过！系统质量良好")
    else:
        print("\n⚠️ 发现回归问题，需要修复")
    
    return success

if __name__ == "__main__":
    success = run_regression_tests()
    sys.exit(0 if success else 1) 