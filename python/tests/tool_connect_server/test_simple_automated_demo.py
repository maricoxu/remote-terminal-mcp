#!/usr/bin/env python3
"""
简单的自动化交互式配置演示
展示如何正确模拟用户输入来实现交互式测试自动化的核心概念
"""

import os
import sys
import tempfile
import yaml
import unittest
from pathlib import Path
from unittest.mock import patch
from io import StringIO

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config_manager.main import EnhancedConfigManager

class TestSimpleAutomationDemo(unittest.TestCase):
    """简单的自动化演示"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / 'config.yaml'
        self.config_manager = EnhancedConfigManager(str(self.config_file))
        self.config_manager.is_mcp_mode = False
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_smart_input_basic_automation(self):
        """测试smart_input基本自动化"""
        print("\n🎯 演示1: 基本smart_input自动化")
        
        # 模拟用户输入
        user_inputs = ['192.168.1.100']
        
        with patch('builtins.input', side_effect=user_inputs):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                result = self.config_manager.smart_input(
                    "🌐 服务器地址",
                    validator=self.config_manager.validate_hostname
                )
                output = mock_stdout.getvalue()
        
        print(f"✅ 输入结果: {result}")
        print(f"📝 输出内容: {output.strip()}")
        
        self.assertEqual(result, '192.168.1.100')
    
    def test_smart_input_error_recovery_automation(self):
        """测试smart_input错误恢复自动化"""
        print("\n🎯 演示2: 错误恢复自动化")
        
        # 模拟用户先输入错误，然后输入正确的值
        user_inputs = [
            'invalid host with spaces',  # 第一次输入错误
            '192.168.1.101'             # 第二次输入正确
        ]
        
        with patch('builtins.input', side_effect=user_inputs):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                result = self.config_manager.smart_input(
                    "🌐 服务器地址",
                    validator=self.config_manager.validate_hostname
                )
                output = mock_stdout.getvalue()
        
        print(f"✅ 最终结果: {result}")
        print(f"📝 错误提示出现: {'输入验证失败' in output}")
        print(f"📝 详细提示出现: {'服务器地址不能包含空格' in output}")
        
        self.assertEqual(result, '192.168.1.101')
        self.assertIn('输入验证失败', output)
        self.assertIn('服务器地址不能包含空格', output)
    
    def test_mcp_guided_setup_automation(self):
        """测试MCP引导配置自动化（无需交互）"""
        print("\n🎯 演示3: MCP引导配置自动化")
        
        # MCP模式的配置是参数化的，不需要用户输入
        result = self.config_manager.mcp_guided_setup(
            server_name='demo-server',
            host='192.168.1.102',
            username='demouser',
            port=22,
            connection_type='ssh',
            description='自动化演示服务器'
        )
        
        print(f"✅ 配置结果: {result}")
        
        # 验证配置文件
        self.assertTrue(self.config_file.exists())
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print(f"📁 配置文件创建: {self.config_file.exists()}")
        print(f"🔧 服务器配置: {config['servers']['demo-server']['host']}")
        
        self.assertIn('demo-server', config['servers'])
        self.assertEqual(config['servers']['demo-server']['host'], '192.168.1.102')
    
    def test_multiple_validation_types(self):
        """测试多种验证类型的自动化"""
        print("\n🎯 演示4: 多种验证类型自动化")
        
        # 测试主机名验证
        with patch('builtins.input', return_value='test-host.com'):
            hostname = self.config_manager.smart_input(
                "主机名", validator=self.config_manager.validate_hostname
            )
        print(f"✅ 主机名验证: {hostname}")
        
        # 测试端口验证
        with patch('builtins.input', return_value='22'):
            port = self.config_manager.smart_input(
                "端口", validator=self.config_manager.validate_port
            )
        print(f"✅ 端口验证: {port}")
        
        # 测试用户名验证
        with patch('builtins.input', return_value='testuser'):
            username = self.config_manager.smart_input(
                "用户名", validator=self.config_manager.validate_username
            )
        print(f"✅ 用户名验证: {username}")
        
        self.assertEqual(hostname, 'test-host.com')
        self.assertEqual(port, '22')
        self.assertEqual(username, 'testuser')

def run_automation_demo():
    """运行自动化演示"""
    print("🤖 交互式配置自动化演示")
    print("=" * 60)
    print("📚 展示如何通过模拟用户输入实现交互式测试自动化")
    print()
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestSimpleAutomationDemo))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=0)  # 降低verbosity以便看到我们的print输出
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("📊 演示结果:")
    print(f"✅ 成功演示: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ 失败演示: {len(result.failures)}")
    print(f"💥 错误演示: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 所有演示成功！")
        print("\n💡 关键要点:")
        print("1. 使用 unittest.mock.patch('builtins.input') 模拟用户输入")
        print("2. side_effect 参数提供输入序列，支持多次输入")
        print("3. 可以测试错误恢复：先输入错误值，再输入正确值")
        print("4. MCP模式的配置是参数化的，不需要交互")
        print("5. 结合 StringIO 可以捕获和验证输出内容")
        
        print("\n🔧 实用技巧:")
        print("• 准确计算需要的输入次数，避免 StopIteration")
        print("• 使用 mock_stdout 验证错误提示和用户指导")
        print("• 分别测试各个功能模块，而不是复杂的完整流程")
        print("• 优先测试核心逻辑，复杂的UI流程可以分解测试")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_automation_demo()
    sys.exit(0 if success else 1) 