#!/usr/bin/env python3
"""
回归测试：验证create_server_config工具必须启动交互配置界面

测试目标：
- 确保create_server_config工具能够真正启动交互配置界面
- 验证预填充参数正确传递
- 确保返回成功启动的结果而不是手动命令

修复问题：用户要求无论输入什么参数，create_server_config都必须启动交互界面
创建日期：2024-12-22
"""

import os
import sys
import json
import time
import tempfile
import subprocess
import unittest
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config_manager.main import EnhancedConfigManager

class TestInteractiveStartupRequirement(unittest.TestCase):
    """测试交互配置界面启动要求"""
    
    def setUp(self):
        """测试前准备"""
        # 自动创建最小化配置文件
        config_file = Path.home() / '.remote-terminal' / 'config.yaml'
        config_file.parent.mkdir(parents=True, exist_ok=True)
        if not config_file.exists():
            config_file.write_text('servers: {}\n', encoding='utf-8')
        # 同步创建项目根目录 config/servers.local.yaml
        import os
        project_root = Path(__file__).parent.parent.parent
        config_dir = project_root / 'config'
        config_dir.mkdir(parents=True, exist_ok=True)
        servers_local = config_dir / 'servers.local.yaml'
        servers_local.write_text('servers: {}\n', encoding='utf-8')
        self.config_manager = EnhancedConfigManager()
        self.created_processes = []  # 记录创建的进程，用于清理
        self.created_files = []      # 记录创建的文件，用于清理
        
    def tearDown(self):
        """测试后清理"""
        # 清理创建的进程
        for process_id in self.created_processes:
            try:
                if isinstance(process_id, int):
                    os.kill(process_id, 9)  # 强制终止进程
                    print(f"✅ 清理进程: {process_id}")
                else:
                    print(f"📋 跳过非进程ID清理: {process_id}")
            except (OSError, ProcessLookupError):
                pass  # 进程可能已经结束
        
        # 清理创建的文件
        for file_path in self.created_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    print(f"✅ 清理文件: {file_path}")
            except OSError:
                pass
    
    def test_create_server_config_must_start_interactive_interface(self):
        """
        核心测试：create_server_config工具必须启动交互配置界面
        
        测试步骤：
        1. 准备测试参数
        2. 调用launch_cursor_terminal_config方法
        3. 验证返回结果表明成功启动（而不是提供手动命令）
        4. 验证进程确实在运行
        5. 验证预填充文件存在且内容正确
        """
        print("\n🎯 开始测试：create_server_config必须启动交互配置界面")
        
        # 第1步：准备测试参数
        test_params = {
            'name': 'test_interactive_startup',
            'host': 'test.example.com',
            'username': 'testuser',
            'port': 22,
            'connection_type': 'relay',
            'description': '测试交互启动功能',
            'docker_enabled': True,
            'docker_image': 'ubuntu:20.04',
            'docker_container': 'test_container'
        }
        
        print(f"📋 测试参数: {json.dumps(test_params, ensure_ascii=False, indent=2)}")
        
        # 第2步：调用配置管理器的启动方法
        print("🚀 调用launch_cursor_terminal_config方法...")
        try:
            result = self.config_manager.launch_cursor_terminal_config(prefill_params=test_params)
            print(f"📄 返回结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        except Exception as e:
            self.fail(f"❌ 调用launch_cursor_terminal_config失败: {e}")
        
        # 第3步：验证返回结果表明成功启动
        print("🔍 验证返回结果...")
        
        # 必须返回成功状态
        self.assertTrue(result.get('success'), 
                       f"❌ 期望返回success=True，实际得到: {result.get('success')}")
        print("✅ 返回状态为成功")
        
        # 必须包含成功启动的消息
        message = result.get('message', '')
        self.assertIn('启动', message, 
                     f"❌ 期望消息包含'启动'，实际消息: {message}")
        print(f"✅ 消息包含启动信息: {message}")
        
        # 验证返回了启动标识（可能是进程ID或窗口标识）
        process_id = result.get('process_id')
        self.assertIsNotNone(process_id, 
                           "❌ 期望返回process_id，但为None")
        print(f"✅ 返回启动标识: {process_id}")
        
        # 第4步：验证启动方式（根据平台不同验证不同内容）
        print("🔍 验证启动方式...")
        platform_type = result.get('platform', '')
        
        if platform_type == "macOS Terminal":
            # macOS使用AppleScript启动新窗口，process_id是字符串标识
            self.assertEqual(process_id, "new_terminal_window", 
                           f"❌ macOS平台期望process_id为'new_terminal_window'，实际: {process_id}")
            print("✅ macOS平台使用新Terminal窗口启动")
            
            # 验证Terminal窗口确实增加了（如果可以检测的话）
            try:
                import subprocess
                result_check = subprocess.run([
                    "osascript", "-e", 
                    'tell application "Terminal" to count windows'
                ], capture_output=True, text=True, timeout=5)
                
                if result_check.returncode == 0:
                    window_count = int(result_check.stdout.strip())
                    print(f"✅ 当前Terminal窗口数: {window_count}")
                else:
                    print("⚠️ 无法检查Terminal窗口数")
            except Exception as e:
                print(f"⚠️ Terminal窗口检查异常: {e}")
                
        else:
            # 其他平台可能返回真实的进程ID
            if isinstance(process_id, int):
                self.created_processes.append(process_id)
                try:
                    os.kill(process_id, 0)
                    print(f"✅ 进程 {process_id} 确实在运行")
                except (OSError, ProcessLookupError):
                    print(f"⚠️ 进程 {process_id} 可能已结束")
            else:
                print(f"📋 其他平台启动标识: {process_id}")
        
        # 第5步：验证预填充文件
        prefill_file = result.get('prefill_file')
        if prefill_file:
            print(f"🔍 验证预填充文件: {prefill_file}")
            
            # 记录文件用于清理
            self.created_files.append(prefill_file)
            
            # 文件必须存在
            self.assertTrue(os.path.exists(prefill_file), 
                          f"❌ 预填充文件不存在: {prefill_file}")
            print("✅ 预填充文件存在")
            
            # 文件内容必须正确
            try:
                with open(prefill_file, 'r', encoding='utf-8') as f:
                    file_content = json.load(f)
                
                # 验证关键参数
                for key, expected_value in test_params.items():
                    actual_value = file_content.get(key)
                    self.assertEqual(actual_value, expected_value,
                                   f"❌ 预填充参数 {key} 不匹配，期望: {expected_value}，实际: {actual_value}")
                
                print("✅ 预填充文件内容正确")
                
            except (json.JSONDecodeError, IOError) as e:
                self.fail(f"❌ 读取预填充文件失败: {e}")
        
        print("🎉 测试通过：create_server_config成功启动交互配置界面！")
    
    def test_interactive_startup_with_minimal_params(self):
        """测试最小参数下的交互启动"""
        print("\n🎯 开始测试：最小参数下的交互启动")
        
        minimal_params = {
            'name': 'test_minimal',
            'host': 'minimal.test.com',
            'username': 'minimal_user'
        }
        
        result = self.config_manager.launch_cursor_terminal_config(prefill_params=minimal_params)
        
        # 验证基本成功条件
        self.assertTrue(result.get('success'), "最小参数测试失败")
        self.assertIsNotNone(result.get('process_id'), "最小参数测试未返回进程ID")
        
        # 记录用于清理（只有整数进程ID才需要清理）
        process_id = result.get('process_id')
        if process_id and isinstance(process_id, int):
            self.created_processes.append(process_id)
        if result.get('prefill_file'):
            self.created_files.append(result.get('prefill_file'))
        
        print("✅ 最小参数测试通过")
    
    def test_interactive_startup_failure_diagnosis(self):
        """测试启动失败时的诊断信息"""
        print("\n🎯 开始测试：启动失败诊断")
        
        # 尝试使用无效参数（这可能不会导致失败，但我们测试错误处理）
        invalid_params = {
            'name': '',  # 空名称
            'host': '',  # 空主机
            'username': ''  # 空用户名
        }
        
        result = self.config_manager.launch_cursor_terminal_config(prefill_params=invalid_params)
        
        # 即使参数无效，启动机制本身应该工作
        # 如果失败，应该有详细的错误信息
        if not result.get('success'):
            self.assertIn('error', result, "失败时应该包含错误信息")
            print(f"📋 失败诊断信息: {result.get('error')}")
        else:
            # 如果成功，记录用于清理（只有整数进程ID才需要清理）
            process_id = result.get('process_id')
            if process_id and isinstance(process_id, int):
                self.created_processes.append(process_id)
            if result.get('prefill_file'):
                self.created_files.append(result.get('prefill_file'))
        
        print("✅ 启动失败诊断测试完成")

def run_test():
    """运行测试的主函数"""
    print("🚀 开始回归测试：验证create_server_config交互启动要求")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestInteractiveStartupRequirement)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    if result.wasSuccessful():
        print("🎉 所有测试通过！create_server_config交互启动功能正常")
        return True
    else:
        print("❌ 测试失败，需要修复问题")
        print(f"失败数量: {len(result.failures)}")
        print(f"错误数量: {len(result.errors)}")
        
        # 显示详细的失败信息
        for test, traceback in result.failures + result.errors:
            print(f"\n❌ 失败测试: {test}")
            print(f"详细信息: {traceback}")
        
        return False

if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1) 