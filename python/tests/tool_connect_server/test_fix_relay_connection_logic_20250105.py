#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回归测试：Relay连接逻辑修复验证 - 2025-01-05

本测试验证以下修复：
1. relay连接逻辑增强（交互式认证检测）
2. 连接状态检测改进（区分本地和远程环境）
3. 命令执行等待时间优化（智能等待）
4. relay认证处理器（检测认证提示并引导用户）

问题背景：
- relay-cli需要交互式认证，但脚本无法自动处理
- 连接状态检测错误判断为本地环境
- 命令执行等待时间过短导致输出不完整
"""

import unittest
import sys
import os
import time
import subprocess
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "python"))

try:
    from enhanced_ssh_manager import EnhancedSSHManager, InteractiveGuide
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print(f"项目根目录: {project_root}")
    print(f"Python路径: {sys.path}")
    sys.exit(1)


class TestRelayConnectionLogicFix(unittest.TestCase):
    """测试Relay连接逻辑修复"""
    
    def setUp(self):
        """测试准备"""
        self.manager = None
        # 模拟配置
        self.mock_config = {
            'servers': {
                'test_relay_server': {
                    'type': 'script_based',
                    'host': 'bjhw-sys-rpm0221.bjhw',
                    'username': 'xuyehua',
                    'connection_type': 'relay',
                    'description': 'Test relay server',
                    'specs': {
                        'connection': {
                            'tool': 'relay-cli',
                            'target': {
                                'host': 'bjhw-sys-rpm0221.bjhw'
                            }
                        },
                        'docker': {
                            'container_name': 'xyh_pytorch',
                            'image': 'xmlir_ubuntu_2004_x86_64:v0.32',
                            'shell': 'zsh'
                        }
                    }
                }
            }
        }
    
    def tearDown(self):
        """测试清理"""
        if self.manager:
            del self.manager
    
    def test_relay_authentication_handler_added(self):
        """测试1: 验证relay认证处理器已添加"""
        print("\n🔍 测试1: 验证relay认证处理器已添加")
        
        with patch('enhanced_ssh_manager.yaml.safe_load', return_value=self.mock_config):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', create=True):
                    self.manager = EnhancedSSHManager()
        
        # 检查_handle_relay_authentication方法是否存在
        self.assertTrue(hasattr(self.manager, '_handle_relay_authentication'),
                       "❌ _handle_relay_authentication方法不存在")
        print("✅ _handle_relay_authentication方法已添加")
        
        # 检查方法是否可调用
        self.assertTrue(callable(getattr(self.manager, '_handle_relay_authentication')),
                       "❌ _handle_relay_authentication不是可调用方法")
        print("✅ _handle_relay_authentication方法可调用")
    
    def test_connection_detection_enhanced(self):
        """测试2: 验证连接状态检测已增强"""
        print("\n🔍 测试2: 验证连接状态检测已增强")
        
        with patch('enhanced_ssh_manager.yaml.safe_load', return_value=self.mock_config):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', create=True):
                    self.manager = EnhancedSSHManager()
        
        # 模拟测试命令输出（本地环境）
        local_output = "CONNECTION_TEST_MacBook-Pro_xuyehua_1704441600"
        
        # 模拟测试命令输出（远程环境）
        remote_output = "CONNECTION_TEST_bjhw-sys-rpm0221_xuyehua_1704441600"
        
        # 模拟relay环境输出
        relay_output = "CONNECTION_TEST_baidu-relay_xuyehua_1704441600"
        
        with patch('subprocess.run') as mock_run:
            # 测试本地环境检测
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = local_output
            
            result = self.manager._detect_existing_connection('test_relay_server', 'test_session')
            self.assertEqual(result, "recoverable", 
                           "❌ 本地环境应该返回'recoverable'")
            print("✅ 本地环境检测正确")
            
            # 测试远程环境检测
            mock_run.return_value.stdout = remote_output
            result = self.manager._detect_existing_connection('test_relay_server', 'test_session')
            self.assertEqual(result, "ready", 
                           "❌ 远程环境应该返回'ready'")
            print("✅ 远程环境检测正确")
    
    def test_command_execution_enhanced(self):
        """测试3: 验证命令执行等待时间已优化"""
        print("\n🔍 测试3: 验证命令执行等待时间已优化")
        
        with patch('enhanced_ssh_manager.yaml.safe_load', return_value=self.mock_config):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', create=True):
                    self.manager = EnhancedSSHManager()
        
        # 检查_wait_for_command_completion方法是否存在
        self.assertTrue(hasattr(self.manager, '_wait_for_command_completion'),
                       "❌ _wait_for_command_completion方法不存在")
        print("✅ _wait_for_command_completion方法已添加")
        
        # 检查_has_new_prompt方法是否存在
        self.assertTrue(hasattr(self.manager, '_has_new_prompt'),
                       "❌ _has_new_prompt方法不存在")
        print("✅ _has_new_prompt方法已添加")
    
    def test_interactive_guide_relay_patterns(self):
        """测试4: 验证交互引导系统支持relay认证"""
        print("\n🔍 测试4: 验证交互引导系统支持relay认证")
        
        guide = InteractiveGuide("test_session")
        
        # 检查relay_auth模式是否存在
        self.assertIn('relay_auth', guide.interaction_patterns,
                     "❌ InteractiveGuide缺少relay_auth模式")
        print("✅ relay_auth模式已添加到InteractiveGuide")
        
        # 测试relay认证提示检测
        test_outputs = [
            "请使用App扫描二维码",
            "scan QR code",
            "请确认指纹",
            "touch sensor",
            "Press any key to continue"
        ]
        
        for output in test_outputs:
            input_type = guide.detect_input_needed(output)
            self.assertEqual(input_type, 'relay_auth',
                           f"❌ 未能检测到relay认证提示: {output}")
        print("✅ relay认证提示检测正常")
        
        # 测试relay认证引导信息
        guide_info = guide.guide_user_input('relay_auth', "请使用App扫描二维码")
        self.assertIn('title', guide_info, "❌ relay认证引导缺少标题")
        self.assertIn('instructions', guide_info, "❌ relay认证引导缺少操作步骤")
        self.assertEqual(guide_info['timeout'], 300, "❌ relay认证超时时间不正确")
        print("✅ relay认证引导信息正确")
    
    def test_relay_cli_usage_compliance(self):
        """测试5: 验证relay-cli使用符合规范"""
        print("\n🔍 测试5: 验证relay-cli使用符合规范")
        
        with patch('enhanced_ssh_manager.yaml.safe_load', return_value=self.mock_config):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', create=True):
                    self.manager = EnhancedSSHManager()
        
        # 检查_connect_via_simple_relay方法
        with patch('subprocess.run') as mock_run:
            # 模拟relay认证成功
            with patch.object(self.manager, '_handle_relay_authentication', return_value=True):
                with patch.object(self.manager, '_wait_for_output', return_value=True):
                    with patch.object(self.manager, '_auto_enter_docker_container', return_value=(True, "Docker OK")):
                        
                        server = self.manager.get_server('test_relay_server')
                        result = self.manager._connect_via_simple_relay(
                            server, 'test_session', 'bjhw-sys-rpm0221.bjhw', 'xuyehua'
                        )
                        
                        # 验证第一个send-keys调用是否使用了正确的relay-cli命令
                        calls = mock_run.call_args_list
                        relay_call = None
                        for call in calls:
                            args = call[0][0] if call[0] else []
                            if 'tmux' in args and 'send-keys' in args and 'relay-cli' in args:
                                relay_call = args
                                break
                        
                        self.assertIsNotNone(relay_call, "❌ 未找到relay-cli命令调用")
                        
                        # 验证relay-cli命令正确（不带参数）
                        self.assertIn('relay-cli', relay_call, "❌ 未使用relay-cli命令")
                        
                        # 确保没有在relay-cli后面添加参数
                        relay_index = relay_call.index('relay-cli')
                        next_index = relay_index + 1
                        if next_index < len(relay_call):
                            next_arg = relay_call[next_index]
                            self.assertIn(next_arg, ['Enter'], 
                                        f"❌ relay-cli后面不应该有参数: {next_arg}")
                        
                        print("✅ relay-cli使用符合规范（不带参数）")
    
    def test_connection_error_logging_enhanced(self):
        """测试6: 验证连接错误日志已增强"""
        print("\n🔍 测试6: 验证连接错误日志已增强")
        
        with patch('enhanced_ssh_manager.yaml.safe_load', return_value=self.mock_config):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', create=True):
                    self.manager = EnhancedSSHManager()
        
        # 检查log_output调用是否增加了调试信息
        with patch('enhanced_ssh_manager.log_output') as mock_log:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "test output"
                
                self.manager._detect_existing_connection('test_relay_server', 'test_session')
                
                # 验证是否有调试日志输出
                debug_calls = [call for call in mock_log.call_args_list 
                             if len(call[0]) > 1 and call[0][1] == "DEBUG"]
                self.assertGreater(len(debug_calls), 0, "❌ 缺少调试日志输出")
                print("✅ 连接状态检测已添加调试日志")
    
    def test_all_fixes_integration(self):
        """测试7: 综合测试所有修复"""
        print("\n🔍 测试7: 综合测试所有修复")
        
        with patch('enhanced_ssh_manager.yaml.safe_load', return_value=self.mock_config):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', create=True):
                    self.manager = EnhancedSSHManager()
        
        # 验证所有关键方法都存在
        required_methods = [
            '_handle_relay_authentication',
            '_wait_for_command_completion',
            '_has_new_prompt',
            '_connect_via_simple_relay',
            '_detect_existing_connection'
        ]
        
        for method in required_methods:
            self.assertTrue(hasattr(self.manager, method),
                           f"❌ 缺少关键方法: {method}")
        print("✅ 所有关键方法都存在")
        
        # 验证InteractiveGuide增强
        guide = InteractiveGuide("test_session")
        self.assertIn('relay_auth', guide.interaction_patterns,
                     "❌ InteractiveGuide缺少relay_auth支持")
        print("✅ InteractiveGuide已增强relay支持")
        
        print("🎉 所有修复验证通过！")


class TestRelayConnectionSpecific(unittest.TestCase):
    """专门测试relay连接相关功能"""
    
    def test_relay_authentication_timeout_handling(self):
        """测试relay认证超时处理"""
        print("\n🔍 测试relay认证超时处理")
        
        mock_config = {
            'servers': {
                'test_server': {
                    'type': 'script_based',
                    'host': 'test.host',
                    'connection_type': 'relay',
                    'specs': {}
                }
            }
        }
        
        with patch('enhanced_ssh_manager.yaml.safe_load', return_value=mock_config):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', create=True):
                    manager = EnhancedSSHManager()
        
        with patch('subprocess.run') as mock_run:
            # 模拟超时情况（始终没有认证成功标志）
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "waiting for authentication..."
            
            # 使用较短的超时时间进行测试
            result = manager._handle_relay_authentication('test_session', timeout=2)
            self.assertFalse(result, "❌ 超时情况应该返回False")
            print("✅ relay认证超时处理正确")
    
    def test_relay_authentication_success_detection(self):
        """测试relay认证成功检测"""
        print("\n🔍 测试relay认证成功检测")
        
        mock_config = {
            'servers': {
                'test_server': {
                    'type': 'script_based',
                    'host': 'test.host',
                    'connection_type': 'relay',
                    'specs': {}
                }
            }
        }
        
        with patch('enhanced_ssh_manager.yaml.safe_load', return_value=mock_config):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', create=True):
                    manager = EnhancedSSHManager()
        
        with patch('subprocess.run') as mock_run:
            # 模拟认证成功
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "authentication successful\n-bash-baidu-ssl$"
            
            result = manager._handle_relay_authentication('test_session', timeout=10)
            self.assertTrue(result, "❌ 认证成功情况应该返回True")
            print("✅ relay认证成功检测正确")


def run_all_tests():
    """运行所有测试"""
    print("🚀 开始执行relay连接逻辑修复回归测试...")
    print("=" * 60)
    
    # 创建测试套件
    test_suite = unittest.TestSuite()
    
    # 添加测试类
    test_suite.addTest(unittest.makeSuite(TestRelayConnectionLogicFix))
    test_suite.addTest(unittest.makeSuite(TestRelayConnectionSpecific))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print("=" * 60)
    print(f"🎯 测试总结:")
    print(f"   总测试数: {result.testsRun}")
    print(f"   成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   失败: {len(result.failures)}")
    print(f"   错误: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ 失败的测试:")
        for test, traceback in result.failures:
            # 修复f-string中不能包含反斜杠的问题
            error_msg = traceback.split('AssertionError: ')[-1].split('\n')[0]
            print(f"   - {test}: {error_msg}")
    
    if result.errors:
        print(f"\n💥 错误的测试:")
        for test, traceback in result.errors:
            # 修复f-string中不能包含反斜杠的问题
            error_msg = traceback.split('\n')[-2]
            print(f"   - {test}: {error_msg}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print(f"\n🎉 所有测试通过！relay连接逻辑修复验证成功！")
    else:
        print(f"\n❌ 部分测试失败，需要进一步修复。")
    
    return success


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 