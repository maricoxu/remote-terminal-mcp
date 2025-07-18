#!/usr/bin/env python3
"""
MCP静默配置回归测试
测试改进后的配置管理器功能：
1. 移除force_interactive参数，默认启用交互模式
2. 改进smart_input的智能错误提示
3. 验证mcp_silent_setup的静默配置功能
"""

import os
import sys
import tempfile
import yaml
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO
import config_manager

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config_manager.main import EnhancedConfigManager
from python.mcp_server import handle_request

class TestMCPSilentConfigRegression(unittest.TestCase):
    """MCP静默配置回归测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时配置目录
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / 'config.yaml'
        
        # 创建配置管理器实例（不需要force_interactive参数）
        self.config_manager = EnhancedConfigManager(str(self.config_file))
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_constructor_without_force_interactive(self):
        """测试构造函数正确处理 force_interactive 参数"""
        # 测试默认构造
        config_manager = EnhancedConfigManager(str(self.config_file))
        self.assertTrue(config_manager.interactive_mode_enabled, "应该默认启用交互模式")
        
        # 测试接受 force_interactive 参数（不再抛出异常）
        config_manager_with_param = EnhancedConfigManager(str(self.config_file), force_interactive=True)
        self.assertTrue(config_manager_with_param.interactive_mode_enabled, "应该启用交互模式")
        
        # 验证兼容性属性存在
        self.assertTrue(hasattr(config_manager, 'io'), "应该有 io 兼容性属性")
        self.assertTrue(hasattr(config_manager, 'ia'), "应该有 ia 兼容性属性")
    
    def test_mcp_silent_setup_basic(self):
        """测试mcp_silent_setup基本功能"""
        result = self.config_manager.mcp_silent_setup(
            name='test-silent-server',
            host='192.168.1.200',
            username='testuser',
            port=2222,
            description='静默配置测试服务器'
        )
        
        self.assertTrue(result['success'], "静默配置应该成功")
        self.assertEqual(result['server_name'], 'test-silent-server')
        
        # 验证配置文件是否正确创建
        self.assertTrue(self.config_file.exists(), "配置文件应该被创建")
        
        # 验证配置内容
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.assertIn('servers', config)
        self.assertIn('test-silent-server', config['servers'])
        
        server_config = config['servers']['test-silent-server']
        self.assertEqual(server_config['host'], '192.168.1.200')
        self.assertEqual(server_config['username'], 'testuser')
        self.assertEqual(server_config['port'], 2222)
        self.assertEqual(server_config['description'], '静默配置测试服务器')
    
    def test_mcp_silent_setup_auto_defaults(self):
        """测试mcp_silent_setup的自动默认值生成"""
        # 只提供必要参数，测试自动生成
        result = self.config_manager.mcp_silent_setup(
            host='192.168.1.201'
        )
        
        self.assertTrue(result['success'], "自动默认值配置应该成功")
        
        server_config = result['server_config']
        self.assertEqual(server_config['host'], '192.168.1.201')
        self.assertEqual(server_config['username'], 'ubuntu')  # 默认用户名
        self.assertEqual(server_config['port'], 22)  # 默认端口
        self.assertEqual(server_config['connection_type'], 'ssh')  # 默认连接类型
        
        # 验证自动生成的服务器名称
        server_name = result['server_name']
        self.assertTrue(server_name.startswith('mcp-server-'))
    
    def test_mcp_silent_setup_validation(self):
        """测试mcp_silent_setup的参数验证"""
        # 测试无效的主机地址
        result = self.config_manager.mcp_silent_setup(
            name='invalid-host-server',
            host='invalid host with spaces',
            username='testuser'
        )
        
        self.assertFalse(result['success'], "无效主机地址应该导致失败")
        self.assertIn('无效的服务器地址', result['error'])
        
        # 测试无效的用户名
        result = self.config_manager.mcp_silent_setup(
            name='invalid-user-server',
            host='192.168.1.202',
            username='invalid@user'
        )
        
        self.assertFalse(result['success'], "无效用户名应该导致失败")
        self.assertIn('无效的用户名', result['error'])
        
        # 测试无效的端口
        result = self.config_manager.mcp_silent_setup(
            name='invalid-port-server',
            host='192.168.1.203',
            username='testuser',
            port=99999
        )
        
        self.assertFalse(result['success'], "无效端口应该导致失败")
        self.assertIn('无效的端口号', result['error'])
    
    def test_smart_input_detailed_error_messages(self):
        """测试smart_input的详细错误信息"""
        # 模拟非MCP模式
        self.config_manager.is_mcp_mode = False
        
        # 测试主机地址验证
        with patch('builtins.input', side_effect=['invalid host', '192.168.1.100']):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                result = self.config_manager.smart_input(
                    "🌐 服务器地址",
                    validator=self.config_manager.validate_hostname
                )
                
                output = mock_stdout.getvalue()
                self.assertIn('输入验证失败', output)
                self.assertIn('服务器地址不能包含空格', output)
                self.assertIn('正确格式示例', output)
                self.assertEqual(result, '192.168.1.100')
        
        # 测试用户名验证（使用无效字符而不是长度）
        with patch('builtins.input', side_effect=['invalid@user', 'validuser']):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                result = self.config_manager.smart_input(
                    "👤 用户名",
                    validator=self.config_manager.validate_username
                )
                
                output = mock_stdout.getvalue()
                self.assertIn('输入验证失败', output)
                self.assertIn('常用用户名', output)
                self.assertEqual(result, 'validuser')
        
        # 测试端口验证
        with patch('builtins.input', side_effect=['99999', '22']):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                result = self.config_manager.smart_input(
                    "🔌 SSH端口",
                    validator=self.config_manager.validate_port
                )
                
                output = mock_stdout.getvalue()
                self.assertIn('端口号必须在1-65535范围内', output)
                self.assertIn('常用端口示例', output)
                self.assertEqual(result, '22')

class TestMCPServerSilentIntegration(unittest.TestCase):
    """MCP服务器静默配置集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / 'config.yaml'
        
        # 设置临时配置路径
        self.original_home = os.environ.get('HOME')
        os.environ['HOME'] = str(Path(self.temp_dir).parent)
        
        # 创建配置目录和有效的配置文件
        config_dir = Path(self.temp_dir).parent / '.remote-terminal'
        config_dir.mkdir(exist_ok=True)
        
        # 创建有效的配置文件内容
        config_content = {
            'servers': {
                'existing-server': {
                    'host': '192.168.1.1',
                    'username': 'testuser',
                    'port': 22,
                    'connection_type': 'ssh',
                    'description': '测试服务器'
                }
            }
        }
        
        config_file = config_dir / 'config.yaml'
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_content, f, allow_unicode=True)
    
    def tearDown(self):
        """测试后清理"""
        # 恢复原始HOME环境变量
        if self.original_home:
            os.environ['HOME'] = self.original_home
        elif 'HOME' in os.environ:
            del os.environ['HOME']
        
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @unittest.skip("集成测试需要完整的MCP环境，暂时跳过")
    def test_create_server_config_tool_silent_mode(self):
        """测试create_server_config工具的静默模式"""
        import asyncio
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "create_server_config",
                "arguments": {
                    "prompt": "创建一个新的服务器配置",
                    "auto_detect": True,
                    "name": "test-mcp-integration",
                    "host": "192.168.1.210",
                    "username": "integrationuser",
                    "port": 2222,
                    "description": "MCP集成测试服务器"
                }
            }
        }
        
        response = asyncio.run(handle_request(request))
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)
        
        content = response["result"]["content"][0]["text"]
        self.assertIn("服务器配置创建成功", content)
        self.assertIn("test-mcp-integration", content)
        self.assertIn("192.168.1.210", content)
    
    @unittest.skip("集成测试需要完整的MCP环境，暂时跳过")
    def test_create_server_config_tool_error_handling(self):
        """测试create_server_config工具的错误处理"""
        import asyncio
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "create_server_config",
                "arguments": {
                    "prompt": "创建一个新的服务器配置",
                    "auto_detect": True,
                    "name": "test-error-server",
                    "host": "invalid host with spaces",  # 无效主机
                    "username": "testuser"
                }
            }
        }
        
        response = asyncio.run(handle_request(request))
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 2)
        self.assertIn("result", response)
        
        content = response["result"]["content"][0]["text"]
        self.assertIn("交互式配置失败", content)
        self.assertIn("无效的服务器地址", content)

def run_silent_config_regression_tests():
    """运行MCP静默配置回归测试"""
    print("🧪 运行MCP静默配置回归测试...")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestMCPSilentConfigRegression))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPServerSilentIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果
    return result.wasSuccessful()

if __name__ == '__main__':
    # 运行回归测试
    success = run_silent_config_regression_tests()
    
    if success:
        print("\n✅ 所有MCP静默配置回归测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 部分MCP静默配置回归测试失败！")
        sys.exit(1) 