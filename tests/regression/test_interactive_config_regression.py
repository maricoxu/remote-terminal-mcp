#!/usr/bin/env python3
"""
交互式配置向导回归测试
测试修复后的MCP配置向导功能是否正常工作
"""

import os
import sys
import tempfile
import yaml
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_config_manager import EnhancedConfigManager

class TestInteractiveConfigRegression(unittest.TestCase):
    """交互式配置向导回归测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时配置目录
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / 'config.yaml'
        
        # 创建配置管理器实例
        self.config_manager = EnhancedConfigManager(str(self.config_file))
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_mcp_mode_detection(self):
        """测试MCP模式检测"""
        # 测试正常终端模式
        with patch('sys.stdout.isatty', return_value=True), \
             patch('sys.stdin.isatty', return_value=True), \
             patch.dict(os.environ, {}, clear=True):
            config_manager = EnhancedConfigManager(str(self.config_file))
            self.assertFalse(config_manager.is_mcp_mode)
        
        # 测试MCP模式（通过环境变量）
        with patch.dict(os.environ, {'MCP_MODE': '1'}):
            config_manager = EnhancedConfigManager(str(self.config_file))
            self.assertTrue(config_manager.is_mcp_mode)
        
        # 测试MCP模式（通过NO_COLOR）
        with patch.dict(os.environ, {'NO_COLOR': '1'}):
            config_manager = EnhancedConfigManager(str(self.config_file))
            self.assertTrue(config_manager.is_mcp_mode)
        
        # 测试MCP模式（通过tty检测）
        with patch('sys.stdout.isatty', return_value=False):
            config_manager = EnhancedConfigManager(str(self.config_file))
            self.assertTrue(config_manager.is_mcp_mode)
    
    def test_mcp_guided_setup_basic(self):
        """测试MCP引导配置基本功能"""
        # 测试基本参数配置
        result = self.config_manager.mcp_guided_setup(
            server_name='test-server',
            host='192.168.1.100',
            username='testuser',
            port=22,
            connection_type='ssh',
            description='测试服务器'
        )
        
        self.assertTrue(result, "MCP引导配置应该成功")
        
        # 验证配置文件是否正确创建
        self.assertTrue(self.config_file.exists(), "配置文件应该被创建")
        
        # 验证配置内容
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.assertIn('servers', config)
        self.assertIn('test-server', config['servers'])
        
        server_config = config['servers']['test-server']
        self.assertEqual(server_config['host'], '192.168.1.100')
        self.assertEqual(server_config['username'], 'testuser')
        self.assertEqual(server_config['port'], 22)
        self.assertEqual(server_config['connection_type'], 'ssh')
        self.assertEqual(server_config['description'], '测试服务器')
    
    def test_mcp_guided_setup_with_docker(self):
        """测试带Docker配置的MCP引导配置"""
        result = self.config_manager.mcp_guided_setup(
            server_name='docker-server',
            host='192.168.1.101',
            username='dockeruser',
            connection_type='ssh',
            use_docker=True,
            docker_image='ubuntu:22.04',
            docker_container='test-container'
        )
        
        self.assertTrue(result, "带Docker的MCP引导配置应该成功")
        
        # 验证Docker配置
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        server_config = config['servers']['docker-server']
        self.assertIn('specs', server_config)
        self.assertIn('docker', server_config['specs'])
        
        docker_config = server_config['specs']['docker']
        self.assertEqual(docker_config['image'], 'ubuntu:22.04')
        self.assertEqual(docker_config['container_name'], 'test-container')
        self.assertTrue(docker_config['auto_create'])
    
    def test_mcp_guided_setup_with_relay(self):
        """测试Relay连接的MCP引导配置"""
        result = self.config_manager.mcp_guided_setup(
            server_name='relay-server',
            host='internal.server.com',
            username='relayuser',
            connection_type='relay',
            relay_target_host='internal.server.com'
        )
        
        self.assertTrue(result, "Relay连接的MCP引导配置应该成功")
        
        # 验证Relay配置
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        server_config = config['servers']['relay-server']
        self.assertEqual(server_config['connection_type'], 'relay')
        self.assertIn('specs', server_config)
        self.assertIn('connection', server_config['specs'])
        
        connection_config = server_config['specs']['connection']
        self.assertEqual(connection_config['tool'], 'relay-cli')
        self.assertIn('target', connection_config)
        self.assertEqual(connection_config['target']['host'], 'internal.server.com')
    
    def test_mcp_guided_setup_auto_generation(self):
        """测试自动生成功能"""
        # 不提供server_name，测试自动生成
        result = self.config_manager.mcp_guided_setup(
            host='192.168.1.102',
            username='autouser'
        )
        
        self.assertTrue(result, "自动生成配置应该成功")
        
        # 验证自动生成的服务器名称
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.assertIn('servers', config)
        server_names = list(config['servers'].keys())
        self.assertEqual(len(server_names), 1)
        
        # 服务器名称应该以mcp-server-开头
        server_name = server_names[0]
        self.assertTrue(server_name.startswith('mcp-server-'))
        
        # 验证默认值
        server_config = config['servers'][server_name]
        self.assertEqual(server_config['port'], 22)
        self.assertEqual(server_config['connection_type'], 'ssh')
    
    def test_mcp_guided_setup_error_handling(self):
        """测试错误处理"""
        # 测试无效的配置参数
        with patch.object(self.config_manager, 'save_config', side_effect=Exception("保存失败")):
            result = self.config_manager.mcp_guided_setup(
                server_name='error-server',
                host='192.168.1.103',
                username='erroruser'
            )
            
            self.assertFalse(result, "发生错误时应该返回False")
    
    def test_guided_setup_mcp_mode_bypass(self):
        """测试原始guided_setup在MCP模式下的行为"""
        # 强制设置MCP模式
        self.config_manager.is_mcp_mode = True
        
        result = self.config_manager.guided_setup()
        
        # 在MCP模式下应该返回False
        self.assertFalse(result, "guided_setup在MCP模式下应该返回False")
    
    def test_config_merge_mode(self):
        """测试配置合并模式"""
        # 首先创建一个服务器配置
        self.config_manager.mcp_guided_setup(
            server_name='server1',
            host='192.168.1.100',
            username='user1'
        )
        
        # 然后添加另一个服务器配置
        self.config_manager.mcp_guided_setup(
            server_name='server2',
            host='192.168.1.101',
            username='user2'
        )
        
        # 验证两个配置都存在
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.assertIn('server1', config['servers'])
        self.assertIn('server2', config['servers'])
        self.assertEqual(len(config['servers']), 2)

class TestMCPServerIntegration(unittest.TestCase):
    """MCP服务器集成测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时配置目录
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / 'config.yaml'
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_interactive_config_wizard_tool_schema(self):
        """测试MCP工具schema是否正确"""
        # 导入MCP服务器模块
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))
        from mcp_server import create_tools_list
        
        tools = create_tools_list()
        
        # 查找interactive_config_wizard工具
        wizard_tool = None
        for tool in tools:
            if tool['name'] == 'interactive_config_wizard':
                wizard_tool = tool
                break
        
        self.assertIsNotNone(wizard_tool, "应该找到interactive_config_wizard工具")
        
        # 验证schema包含新增的参数
        properties = wizard_tool['inputSchema']['properties']
        expected_params = [
            'server_name', 'host', 'username', 'port', 'connection_type',
            'relay_target_host', 'use_docker', 'docker_image', 'docker_container', 'description'
        ]
        
        for param in expected_params:
            self.assertIn(param, properties, f"Schema应该包含参数: {param}")
    
    def test_mcp_server_tool_parameters(self):
        """测试MCP服务器工具参数传递"""
        # 模拟MCP工具调用参数
        test_params = {
            'server_name': 'mcp-test-server',
            'host': '10.0.0.1',
            'username': 'mcpuser',
            'port': 2222,
            'connection_type': 'ssh',
            'use_docker': True,
            'docker_image': 'python:3.9',
            'docker_container': 'mcp-container',
            'description': 'MCP测试服务器'
        }
        
        # 创建配置管理器并测试mcp_guided_setup
        config_manager = EnhancedConfigManager(str(self.config_file))
        result = config_manager.mcp_guided_setup(**test_params)
        
        self.assertTrue(result, "MCP引导配置应该成功")
        
        # 验证所有参数都被正确应用
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        server_config = config['servers']['mcp-test-server']
        self.assertEqual(server_config['host'], '10.0.0.1')
        self.assertEqual(server_config['username'], 'mcpuser')
        self.assertEqual(server_config['port'], 2222)
        self.assertEqual(server_config['connection_type'], 'ssh')
        self.assertEqual(server_config['description'], 'MCP测试服务器')
        
        # 验证Docker配置
        docker_config = server_config['specs']['docker']
        self.assertEqual(docker_config['image'], 'python:3.9')
        self.assertEqual(docker_config['container_name'], 'mcp-container')

def run_regression_tests():
    """运行所有回归测试"""
    print("🚀 开始运行交互式配置向导回归测试")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestInteractiveConfigRegression))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPServerIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果摘要
    print("\n" + "=" * 60)
    print("📊 测试结果摘要:")
    print(f"✅ 成功测试: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ 失败测试: {len(result.failures)}")
    print(f"💥 错误测试: {len(result.errors)}")
    print(f"📈 总测试数: {result.testsRun}")
    
    if result.failures:
        print("\n🔍 失败的测试:")
        for test, traceback in result.failures:
            print(f"  • {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n💥 错误的测试:")
        for test, traceback in result.errors:
            print(f"  • {test}: {traceback.split('Exception:')[-1].strip()}")
    
    # 返回测试是否全部通过
    return len(result.failures) == 0 and len(result.errors) == 0

if __name__ == '__main__':
    success = run_regression_tests()
    sys.exit(0 if success else 1) 