#!/usr/bin/env python3
"""
自动同步配置界面增强回归测试

测试目的：验证配置界面中新增的自动同步配置功能
- _configure_sync()方法功能完整性
- 用户交互流程正确性
- 配置参数传递和验证
- 与现有配置流程的集成
- 错误处理和默认值设置

作者：按用户建议实现
日期：2024年实现
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from io import StringIO
import config_manager

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def log_test_output(message: str, level: str = "INFO"):
    """测试日志输出"""
    levels = {"DEBUG": "🔍", "INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}
    prefix = levels.get(level, "ℹ️")
    print(f"{prefix} {message}")

class TestSyncConfigUIEnhancement(unittest.TestCase):
    """自动同步配置界面增强测试"""
    
    def setUp(self):
        """测试setup"""
        self.test_name = "TestSyncConfigUIEnhancement"
        log_test_output(f"开始测试: {self.test_name}", "INFO")
    
    def tearDown(self):
        """测试teardown"""
        log_test_output(f"完成测试: {self.test_name}", "INFO")
    
    def test_configure_sync_method_exists(self):
        """测试1: _configure_sync方法存在且可调用"""
        log_test_output("测试1: _configure_sync方法存在性", "INFO")
        
        try:
            from config_manager.main import EnhancedConfigManager
            
            # 创建配置管理器实例
            config_manager = EnhancedConfigManager()
            
            # 验证方法存在
            self.assertTrue(hasattr(config_manager, '_configure_sync'))
            self.assertTrue(callable(getattr(config_manager, '_configure_sync')))
            
            log_test_output("✅ _configure_sync方法存在且可调用", "SUCCESS")
            
        except ImportError as e:
            self.fail(f"无法导入EnhancedConfigManager: {str(e)}")
        except Exception as e:
            self.fail(f"测试_configure_sync方法存在性失败: {str(e)}")
    
    def test_collect_sync_patterns_method_exists(self):
        """测试2: _collect_sync_patterns方法存在且可调用"""
        log_test_output("测试2: _collect_sync_patterns方法存在性", "INFO")
        
        try:
            from config_manager.main import EnhancedConfigManager
            
            # 创建配置管理器实例
            config_manager = EnhancedConfigManager()
            
            # 验证方法存在
            self.assertTrue(hasattr(config_manager, '_collect_sync_patterns'))
            self.assertTrue(callable(getattr(config_manager, '_collect_sync_patterns')))
            
            log_test_output("✅ _collect_sync_patterns方法存在且可调用", "SUCCESS")
            
        except ImportError as e:
            self.fail(f"无法导入EnhancedConfigManager: {str(e)}")
        except Exception as e:
            self.fail(f"测试_collect_sync_patterns方法存在性失败: {str(e)}")
    
    @patch('config_manager.main.EnhancedConfigManager.smart_input')
    @patch('config_manager.main.EnhancedConfigManager.colored_print')
    def test_configure_sync_disabled(self, mock_colored_print, mock_smart_input):
        """测试3: 用户选择不启用自动同步"""
        log_test_output("测试3: 用户选择不启用自动同步", "INFO")
        
        try:
            from config_manager.main import EnhancedConfigManager
            
            # 创建配置管理器实例
            config_manager = EnhancedConfigManager()
            
            # 模拟用户选择不启用同步
            mock_smart_input.return_value = "2"
            
            # 调用_configure_sync方法
            result = config_manager._configure_sync()
            
            # 验证结果
            self.assertIsNone(result)
            
            # 验证smart_input被调用
            mock_smart_input.assert_called_once()
            
            log_test_output("✅ 用户选择不启用同步时正确返回None", "SUCCESS")
            
        except Exception as e:
            self.fail(f"测试用户选择不启用同步失败: {str(e)}")
    
    @patch('config_manager.main.EnhancedConfigManager.smart_input')
    @patch('config_manager.main.EnhancedConfigManager.colored_print')
    @patch('config_manager.main.EnhancedConfigManager._collect_sync_patterns')
    def test_configure_sync_enabled_full_config(self, mock_collect_patterns, mock_colored_print, mock_smart_input):
        """测试4: 用户启用自动同步并完整配置"""
        log_test_output("测试4: 用户启用自动同步并完整配置", "INFO")
        
        try:
            from config_manager.main import EnhancedConfigManager
            
            # 创建配置管理器实例
            config_manager = EnhancedConfigManager()
            
            # 模拟用户输入序列
            mock_smart_input.side_effect = [
                "1",  # 启用自动同步
                "/home/Code",  # 远程工作目录
                "8021",  # FTP端口
                "ftpuser",  # FTP用户名
                "mypassword",  # FTP密码
                "/local/workspace"  # 本地工作目录
            ]
            
            # 模拟collect_sync_patterns返回值
            mock_collect_patterns.side_effect = [
                ['*.py', '*.js', '*.md'],  # 包含模式
                ['*.pyc', '__pycache__', '.git']  # 排除模式
            ]
            
            # 调用_configure_sync方法
            result = config_manager._configure_sync()
            
            # 验证结果
            self.assertIsNotNone(result)
            self.assertIsInstance(result, dict)
            self.assertTrue(result.get('enabled'))
            self.assertEqual(result.get('remote_workspace'), '/home/Code')
            self.assertEqual(result.get('ftp_port'), '8021')
            self.assertEqual(result.get('ftp_user'), 'ftpuser')
            self.assertEqual(result.get('ftp_password'), 'mypassword')
            self.assertEqual(result.get('local_workspace'), '/local/workspace')
            self.assertEqual(result.get('include_patterns'), ['*.py', '*.js', '*.md'])
            self.assertEqual(result.get('exclude_patterns'), ['*.pyc', '__pycache__', '.git'])
            
            # 验证smart_input被正确调用
            self.assertEqual(mock_smart_input.call_count, 6)
            
            # 验证_collect_sync_patterns被调用两次
            self.assertEqual(mock_collect_patterns.call_count, 2)
            
            log_test_output("✅ 用户启用同步时正确收集所有配置", "SUCCESS")
            
        except Exception as e:
            self.fail(f"测试用户启用同步配置失败: {str(e)}")
    
    @patch('config_manager.main.EnhancedConfigManager.smart_input')
    @patch('config_manager.main.EnhancedConfigManager.colored_print')
    @patch('config_manager.main.EnhancedConfigManager._collect_sync_patterns')
    def test_configure_sync_with_defaults(self, mock_collect_patterns, mock_colored_print, mock_smart_input):
        """测试5: 使用默认值配置自动同步"""
        log_test_output("测试5: 使用默认值配置自动同步", "INFO")
        
        try:
            from config_manager.main import EnhancedConfigManager
            
            # 创建配置管理器实例
            config_manager = EnhancedConfigManager()
            
            # 准备默认配置
            defaults = {
                'enabled': True,
                'remote_workspace': '/test/workspace',
                'ftp_port': 9021,
                'ftp_user': 'testuser',
                'ftp_password': 'testpassword',
                'local_workspace': '/test/local',
                'include_patterns': ['*.test'],
                'exclude_patterns': ['*.temp']
            }
            
            # 模拟用户输入序列（使用默认值）
            mock_smart_input.side_effect = [
                "1",  # 启用自动同步
                "/test/workspace",  # 远程工作目录（使用默认值）
                "9021",  # FTP端口（使用默认值）
                "testuser",  # FTP用户名（使用默认值）
                "testpassword",  # FTP密码（使用默认值）
                "/test/local"  # 本地工作目录（使用默认值）
            ]
            
            # 模拟collect_sync_patterns返回默认值
            mock_collect_patterns.side_effect = [
                ['*.test'],  # 包含模式
                ['*.temp']   # 排除模式
            ]
            
            # 调用_configure_sync方法
            result = config_manager._configure_sync(defaults)
            
            # 验证结果
            self.assertIsNotNone(result)
            self.assertEqual(result.get('remote_workspace'), '/test/workspace')
            self.assertEqual(result.get('ftp_port'), '9021')
            self.assertEqual(result.get('ftp_user'), 'testuser')
            self.assertEqual(result.get('ftp_password'), 'testpassword')
            self.assertEqual(result.get('local_workspace'), '/test/local')
            
            log_test_output("✅ 默认值配置正确应用", "SUCCESS")
            
        except Exception as e:
            self.fail(f"测试默认值配置失败: {str(e)}")
    
    @patch('config_manager.main.EnhancedConfigManager.smart_input')
    @patch('config_manager.main.EnhancedConfigManager.colored_print')
    def test_collect_sync_patterns_with_defaults(self, mock_colored_print, mock_smart_input):
        """测试6: _collect_sync_patterns方法处理默认值"""
        log_test_output("测试6: _collect_sync_patterns处理默认值", "INFO")
        
        try:
            from config_manager.main import EnhancedConfigManager
            
            # 创建配置管理器实例
            config_manager = EnhancedConfigManager()
            
            # 模拟用户输入（保留默认值，不添加新值）
            mock_smart_input.side_effect = [
                "*.py",  # 保留第一个默认值
                "*.js",  # 保留第二个默认值
                ""       # 完成配置
            ]
            
            # 调用_collect_sync_patterns方法
            result = config_manager._collect_sync_patterns(
                "包含模式", 
                defaults=['*.py', '*.js']
            )
            
            # 验证结果
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)
            self.assertIn('*.py', result)
            self.assertIn('*.js', result)
            
            log_test_output("✅ _collect_sync_patterns正确处理默认值", "SUCCESS")
            
        except Exception as e:
            self.fail(f"测试_collect_sync_patterns处理默认值失败: {str(e)}")
    
    @patch('config_manager.main.EnhancedConfigManager.smart_input')
    @patch('config_manager.main.EnhancedConfigManager.colored_print')
    def test_collect_sync_patterns_add_new(self, mock_colored_print, mock_smart_input):
        """测试7: _collect_sync_patterns方法添加新模式"""
        log_test_output("测试7: _collect_sync_patterns添加新模式", "INFO")
        
        try:
            from config_manager.main import EnhancedConfigManager
            
            # 创建配置管理器实例
            config_manager = EnhancedConfigManager()
            
            # 模拟用户输入（保留默认值，添加新值）
            mock_smart_input.side_effect = [
                "*.py",     # 保留第一个默认值
                "*.ts",     # 添加新的模式
                "*.vue",    # 添加新的模式
                ""          # 完成配置
            ]
            
            # 调用_collect_sync_patterns方法
            result = config_manager._collect_sync_patterns(
                "包含模式", 
                defaults=['*.py']
            )
            
            # 验证结果
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 3)
            self.assertIn('*.py', result)
            self.assertIn('*.ts', result)
            self.assertIn('*.vue', result)
            
            log_test_output("✅ _collect_sync_patterns正确添加新模式", "SUCCESS")
            
        except Exception as e:
            self.fail(f"测试_collect_sync_patterns添加新模式失败: {str(e)}")
    
    @patch('config_manager.main.EnhancedConfigManager.guided_setup')
    def test_guided_setup_integration(self, mock_guided_setup):
        """测试8: guided_setup集成自动同步配置"""
        log_test_output("测试8: guided_setup集成自动同步配置", "INFO")
        
        try:
            from config_manager.main import EnhancedConfigManager
            
            # 创建配置管理器实例
            config_manager = EnhancedConfigManager()
            
            # 模拟guided_setup返回值
            mock_guided_setup.return_value = ("test_server", {
                'connection_type': 'ssh',
                'host': 'test.example.com',
                'username': 'testuser',
                'docker_enabled': True,
                'docker_config': {},
                'auto_sync_enabled': True,
                'sync_config': {
                    'enabled': True,
                    'remote_workspace': '/home/Code',
                    'ftp_port': '8021',
                    'ftp_user': 'ftpuser',
                    'ftp_password': 'syncpassword'
                }
            })
            
            # 调用guided_setup方法
            result = config_manager.guided_setup()
            
            # 验证结果
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 2)
            
            server_name, config = result
            self.assertEqual(server_name, "test_server")
            self.assertIn('sync_config', config)
            self.assertTrue(config.get('auto_sync_enabled'))
            
            log_test_output("✅ guided_setup正确集成自动同步配置", "SUCCESS")
            
        except Exception as e:
            self.fail(f"测试guided_setup集成失败: {str(e)}")

if __name__ == '__main__':
    print("🧪 自动同步配置界面增强回归测试")
    print("=" * 50)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSyncConfigUIEnhancement)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出测试结果
    if result.wasSuccessful():
        print("\n✅ 所有测试通过！")
        print(f"📊 测试统计: {result.testsRun}个测试，{len(result.failures)}个失败，{len(result.errors)}个错误")
        exit(0)
    else:
        print("\n❌ 测试失败！")
        print(f"📊 测试统计: {result.testsRun}个测试，{len(result.failures)}个失败，{len(result.errors)}个错误")
        exit(1) 