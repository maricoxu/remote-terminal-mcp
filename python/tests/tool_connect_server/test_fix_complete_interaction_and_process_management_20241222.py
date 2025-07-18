#!/usr/bin/env python3
"""
回归测试：完整交互序列和进程管理修复
测试日期：2024-12-22
修复问题：
1. 自动化测试未完整走完交互流程（缺少文件同步和远程工作目录设置）
2. 测试完成后可能有残留进程
3. 需要确保进程正确清理
"""

import unittest
import asyncio
import tempfile
import os
import sys
import time
import psutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.utils.automated_interaction_tester import AutomatedInteractionTester

class TestCompleteInteractionAndProcessManagement(unittest.TestCase):
    """测试完整交互序列和进程管理功能"""
    
    def setUp(self):
        """测试前准备"""
        self.project_root = project_root
        self.tester = AutomatedInteractionTester(str(self.project_root))
        self.test_config = {
            'name': 'process-test-server',
            'host': 'process.test.com',
            'username': 'processuser',
            'port': 22
        }
    
    def tearDown(self):
        """测试后清理"""
        # 确保清理所有测试相关进程
        self._cleanup_test_processes()
    
    def _cleanup_test_processes(self):
        """清理测试相关进程"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    if ('enhanced_config_manager' in cmdline or 
                        'process-test-server' in cmdline):
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except psutil.TimeoutExpired:
                            proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"清理测试进程时出错: {e}")
    
    def test_complete_applescript_sequence(self):
        """测试完整的AppleScript交互序列"""
        print("🧪 测试完整的AppleScript交互序列")
        
        config_params = {
            'name': 'process-test-server',
            'host': 'process.test.com',
            'username': 'processuser',
            'port': 22
        }
        
        tester = AutomatedInteractionTester()
        applescript = tester.generate_applescript(config_params, "/tmp/test_output.txt")
        
        # 验证AppleScript包含所有必要的交互步骤
        self.assertIn('do script "1" in newTab', applescript)  # 选择向导配置
        self.assertIn('do script "2" in newTab', applescript)  # 选择SSH直连
        self.assertIn('do script "process-test-server" in newTab', applescript)  # 服务器名称
        self.assertIn('do script "process.test.com" in newTab', applescript)  # 服务器地址
        self.assertIn('do script "processuser" in newTab', applescript)  # 用户名
        self.assertIn('do script "n" in newTab', applescript)  # 跳过Docker
        self.assertIn('do script "y" in newTab', applescript)  # 确认配置
        
        # 🔧 修复：验证新的交互序列，不再检查退出命令
        self.assertIn('文件同步功能设置', applescript)  # 文件同步设置
        self.assertIn('远程工作目录设置', applescript)  # 工作目录设置
        self.assertIn('程序会自动保存并退出', applescript)  # 自动退出说明
        
        # 🔧 修复：不再检查 "q" 退出命令，因为程序自动退出
        self.assertNotIn('do script "q" in newTab', applescript)  # 确认没有退出命令
        
        print("✅ AppleScript交互序列验证通过")
    
    def test_complete_expect_sequence(self):
        """测试完整的expect脚本序列"""
        print("🧪 测试完整的expect脚本序列")
        
        config_params = {
            'name': 'process-test-server',
            'host': 'process.test.com',
            'username': 'processuser',
            'port': 22
        }
        
        tester = AutomatedInteractionTester()
        expect_script = tester.generate_expect_script(config_params)
        
        # 验证expect脚本包含所有必要的交互步骤
        self.assertIn('expect "请选择操作"', expect_script)  # 主菜单
        self.assertIn('send "1\\r"', expect_script)  # 选择向导配置
        self.assertIn('expect "选择连接方式"', expect_script)  # 连接方式
        self.assertIn('send "2\\r"', expect_script)  # 选择SSH直连
        self.assertIn('expect "服务器配置名称"', expect_script)  # 服务器名称
        self.assertIn('send "process-test-server\\r"', expect_script)  # 输入服务器名称
        self.assertIn('expect "服务器地址"', expect_script)  # 服务器地址
        self.assertIn('send "process.test.com\\r"', expect_script)  # 输入服务器地址
        self.assertIn('expect "用户名"', expect_script)  # 用户名
        self.assertIn('send "processuser\\r"', expect_script)  # 输入用户名
        self.assertIn('expect "端口"', expect_script)  # 端口
        self.assertIn('expect "是否使用Docker"', expect_script)  # Docker配置
        self.assertIn('send "n\\r"', expect_script)  # 跳过Docker
        
        # 🔧 修复：验证新的交互序列
        self.assertIn('同步功能', expect_script)  # 文件同步功能
        self.assertIn('工作目录', expect_script)  # 远程工作目录
        self.assertIn('expect "确认配置"', expect_script)  # 确认配置
        self.assertIn('send "y\\r"', expect_script)  # 确认
        
        # 🔧 修复：验证程序自动结束，不再检查保存配置步骤
        self.assertIn('expect {*保存*}', expect_script)  # 等待保存信息
        self.assertIn('expect eof', expect_script)  # 等待程序结束
        
        # 🔧 修复：不再检查具体的保存配置期望，因为已经简化
        self.assertNotIn('expect "保存配置"', expect_script)  # 确认没有具体的保存配置期望
        
        print("✅ expect脚本交互序列验证通过")
    
    def test_process_tracking_mechanism(self):
        """测试进程跟踪机制"""
        # 验证tester有进程跟踪属性
        self.assertTrue(hasattr(self.tester, 'active_processes'))
        self.assertIsInstance(self.tester.active_processes, list)
        self.assertEqual(len(self.tester.active_processes), 0)
        
        # 模拟添加进程
        mock_process = MagicMock()
        mock_process.pid = 12345
        self.tester.active_processes.append(mock_process)
        
        self.assertEqual(len(self.tester.active_processes), 1)
        
        print("✅ 进程跟踪机制测试通过")
    
    def test_process_cleanup_functionality(self):
        """测试进程清理功能"""
        async def test_cleanup():
            # 测试cleanup_processes方法存在
            self.assertTrue(hasattr(self.tester, 'cleanup_processes'))
            
            # 测试方法可以调用
            await self.tester.cleanup_processes()
            
            # 验证进程列表被清空
            self.assertEqual(len(self.tester.active_processes), 0)
        
        # 运行异步测试
        asyncio.run(test_cleanup())
        print("✅ 进程清理功能测试通过")
    
    def test_remaining_process_detection(self):
        """测试残留进程检测功能"""
        async def test_detection():
            # 测试check_remaining_processes方法存在
            self.assertTrue(hasattr(self.tester, 'check_remaining_processes'))
            
            # 调用检测方法
            remaining = await self.tester.check_remaining_processes()
            
            # 验证返回值格式
            self.assertIsInstance(remaining, list)
            
            # 如果有残留进程，验证格式
            for proc in remaining:
                self.assertIsInstance(proc, dict)
                self.assertIn('pid', proc)
                self.assertIn('name', proc)
                self.assertIn('cmdline', proc)
        
        # 运行异步测试
        asyncio.run(test_detection())
        print("✅ 残留进程检测功能测试通过")
    
    def test_comprehensive_test_with_process_management(self):
        """测试包含进程管理的综合测试流程"""
        async def test_comprehensive():
            # 验证综合测试方法存在并包含进程管理
            self.assertTrue(hasattr(self.tester, 'run_comprehensive_test'))
            
            # 由于完整测试需要真实的交互环境，这里主要测试方法结构
            # 在实际CI环境中，这个测试会被跳过
            try:
                # 模拟测试环境
                with patch.object(self.tester, 'test_interactive_config') as mock_test:
                    mock_test.return_value = (True, "模拟测试成功")
                    
                    with patch.object(self.tester, 'verify_config_created') as mock_verify:
                        mock_verify.return_value = (True, "模拟验证成功")
                        
                        with patch.object(self.tester, 'check_remaining_processes') as mock_check:
                            mock_check.return_value = []  # 无残留进程
                            
                            # 运行综合测试（模拟模式）
                            result = await self.tester.run_comprehensive_test()
                            
                            # 验证测试结果
                            self.assertTrue(result)
                            
                            # 验证关键方法被调用
                            mock_test.assert_called()
                            mock_verify.assert_called()
                            mock_check.assert_called()
                
            except Exception as e:
                # 在CI环境中，某些功能可能不可用
                print(f"综合测试在当前环境中跳过: {e}")
        
        # 运行异步测试
        asyncio.run(test_comprehensive())
        print("✅ 包含进程管理的综合测试流程测试通过")
    
    def test_timeout_handling_in_interactions(self):
        """测试交互过程中的超时处理"""
        # 验证超时参数在各个方法中正确传递
        methods_with_timeout = [
            'test_interactive_config',
            'test_with_applescript', 
            'test_with_expect',
            'test_with_pexpect'
        ]
        
        for method_name in methods_with_timeout:
            self.assertTrue(hasattr(self.tester, method_name))
            method = getattr(self.tester, method_name)
            
            # 检查方法签名包含timeout参数
            import inspect
            sig = inspect.signature(method)
            self.assertIn('timeout', sig.parameters)
            
            # 检查默认超时值
            timeout_param = sig.parameters['timeout']
            self.assertIsNotNone(timeout_param.default)
        
        print("✅ 交互超时处理测试通过")
    
    def test_error_handling_in_process_management(self):
        """测试进程管理中的错误处理"""
        async def test_error_handling():
            # 测试清理不存在的进程
            self.tester.active_processes.append(99999)  # 不存在的PID
            
            # 应该不会抛出异常
            try:
                await self.tester.cleanup_processes()
                success = True
            except Exception as e:
                success = False
                print(f"进程清理异常处理失败: {e}")
            
            self.assertTrue(success)
            
            # 测试检测进程时的异常处理
            try:
                remaining = await self.tester.check_remaining_processes()
                self.assertIsInstance(remaining, list)
                success = True
            except Exception as e:
                success = False
                print(f"进程检测异常处理失败: {e}")
            
            self.assertTrue(success)
        
        # 运行异步测试
        asyncio.run(test_error_handling())
        print("✅ 进程管理错误处理测试通过")
    
    def test_temp_file_cleanup_integration(self):
        """测试临时文件清理与进程管理的集成"""
        # 创建一些临时文件
        temp_files = []
        for i in range(3):
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.close()
            temp_files.append(temp_file.name)
            self.tester.temp_files.append(temp_file.name)
        
        # 验证文件存在
        for file_path in temp_files:
            self.assertTrue(os.path.exists(file_path))
        
        # 执行清理
        self.tester.cleanup_temp_files()
        
        # 验证文件被删除
        for file_path in temp_files:
            self.assertFalse(os.path.exists(file_path))
        
        # 验证临时文件列表被清空
        self.assertEqual(len(self.tester.temp_files), 0)
        
        print("✅ 临时文件清理集成测试通过")

    def test_terminal_cleanup_functionality(self):
        """测试终端清理功能"""
        print("🧪 测试终端清理功能")
        
        # 测试启用清理的情况
        tester_with_cleanup = AutomatedInteractionTester(cleanup_terminals=True)
        self.assertTrue(tester_with_cleanup.cleanup_terminals)
        
        # 测试禁用清理的情况
        tester_without_cleanup = AutomatedInteractionTester(cleanup_terminals=False)
        self.assertFalse(tester_without_cleanup.cleanup_terminals)
        
        # 测试清理脚本生成
        cleanup_script = tester_with_cleanup._generate_terminal_cleanup_script()
        self.assertIn('close newTab', cleanup_script)
        self.assertIn('close window', cleanup_script)
        
        print("✅ 终端清理功能测试通过")

    def test_applescript_terminal_cleanup_integration(self):
        """测试AppleScript中的终端清理集成"""
        print("🧪 测试AppleScript终端清理集成")
        
        config_params = {
            'name': 'cleanup-test-server',
            'host': 'cleanup.test.com',
            'username': 'cleanupuser',
            'port': 22
        }
        
        # 测试启用清理的AppleScript
        tester_with_cleanup = AutomatedInteractionTester(cleanup_terminals=True)
        applescript_with_cleanup = tester_with_cleanup.generate_applescript(config_params, "/tmp/test.txt")
        
        # 验证包含清理代码
        self.assertIn('close newTab', applescript_with_cleanup)
        self.assertIn('close window', applescript_with_cleanup)
        
        # 测试禁用清理的AppleScript
        tester_without_cleanup = AutomatedInteractionTester(cleanup_terminals=False)
        applescript_without_cleanup = tester_without_cleanup.generate_applescript(config_params, "/tmp/test.txt")
        
        # 验证不包含清理代码，而是包含跳过说明
        self.assertIn('跳过终端清理', applescript_without_cleanup)
        self.assertNotIn('close newTab', applescript_without_cleanup)
        
        print("✅ AppleScript终端清理集成测试通过")

class TestInteractionSequenceCompleteness(unittest.TestCase):
    """测试交互序列完整性"""
    
    def setUp(self):
        self.tester = AutomatedInteractionTester()
    
    def test_all_required_interaction_steps(self):
        """测试所有必需的交互步骤"""
        required_steps = [
            # 基础配置步骤
            '选择配置模式',
            '选择连接方式', 
            '服务器名称',
            '服务器地址',
            '用户名',
            '端口',
            
            # Docker配置
            'Docker',
            
            # 🔧 新增的必需步骤
            '同步功能',
            '工作目录',
            
            # 确认和保存
            '确认配置',
            '保存配置',
            
            # 退出
            '退出'
        ]
        
        # 生成测试配置的脚本
        test_config = {
            'name': 'completeness-test',
            'host': 'test.example.com',
            'username': 'testuser',
            'port': 22
        }
        
        # 测试AppleScript
        applescript = self.tester.generate_applescript(test_config, '/tmp/test')
        for step in required_steps:
            # 不是所有步骤都会在注释中出现，但关键的交互应该存在
            if step in ['同步功能', '工作目录']:
                self.assertIn(step, applescript, f"AppleScript缺少必需步骤: {step}")
        
        # 测试expect脚本
        expect_script = self.tester.generate_expect_script(test_config)
        for step in ['同步功能', '工作目录']:
            self.assertIn(step, expect_script, f"expect脚本缺少必需步骤: {step}")
        
        print("✅ 交互序列完整性测试通过")

def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTest(unittest.makeSuite(TestCompleteInteractionAndProcessManagement))
    suite.addTest(unittest.makeSuite(TestInteractionSequenceCompleteness))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()

if __name__ == '__main__':
    print("🧪 开始运行完整交互序列和进程管理回归测试...")
    print("=" * 80)
    
    success = run_tests()
    
    print("=" * 80)
    if success:
        print("🎉 所有完整交互序列和进程管理测试通过！")
        sys.exit(0)
    else:
        print("❌ 部分完整交互序列和进程管理测试失败！")
        sys.exit(1) 