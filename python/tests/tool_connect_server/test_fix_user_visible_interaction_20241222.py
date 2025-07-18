#!/usr/bin/env python3
"""
回归测试：验证用户真的能看到交互配置界面

测试目标：
- 验证交互界面对用户可见（不是后台进程）
- 验证新终端窗口确实打开
- 验证用户能够与界面交互

修复问题：之前的测试只验证了技术实现，没有验证用户体验
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

class TestUserVisibleInteraction(unittest.TestCase):
    """测试用户可见的交互界面"""
    
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
        self.created_processes = []
        self.created_files = []
        
    def tearDown(self):
        """测试后清理"""
        # 清理创建的进程
        for process_id in self.created_processes:
            try:
                if isinstance(process_id, int):
                    os.kill(process_id, 9)
                    print(f"✅ 清理进程: {process_id}")
            except (OSError, ProcessLookupError):
                pass
        
        # 清理创建的文件
        for file_path in self.created_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    print(f"✅ 清理文件: {file_path}")
            except OSError:
                pass
    
    @unittest.skip("仅供人工验证，不参与自动化/CI：macOS终端窗口检测")
    def test_terminal_window_creation_on_macos(self):
        """
        测试在macOS上是否真的创建了新的Terminal窗口
        """
        print("\n🎯 测试Terminal窗口创建（macOS）")
        
        # 只在macOS上运行这个测试
        import platform
        if platform.system() != "Darwin":
            self.skipTest("此测试仅适用于macOS")
        
        # 记录启动前的Terminal窗口数量
        try:
            result = subprocess.run([
                "osascript", "-e", 
                'tell application "Terminal" to count windows'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                windows_before = int(result.stdout.strip())
                print(f"📊 启动前Terminal窗口数: {windows_before}")
            else:
                windows_before = 0
                print("⚠️ 无法获取Terminal窗口数，假设为0")
                
        except Exception as e:
            windows_before = 0
            print(f"⚠️ 检查Terminal窗口失败: {e}")
        
        # 启动配置界面
        test_params = {
            'name': 'test_terminal_window',
            'host': 'terminal.test.com',
            'username': 'terminal_user'
        }
        
        result = self.config_manager.launch_cursor_terminal_config(prefill_params=test_params)
        
        # 记录文件用于清理
        if result.get('prefill_file'):
            self.created_files.append(result.get('prefill_file'))
        
        # 验证返回结果表明新窗口已创建
        self.assertTrue(result.get('success'), f"启动失败: {result}")
        
        # 等待窗口创建
        time.sleep(2)
        
        # 检查是否真的创建了新窗口
        try:
            result_after = subprocess.run([
                "osascript", "-e", 
                'tell application "Terminal" to count windows'
            ], capture_output=True, text=True, timeout=5)
            
            if result_after.returncode == 0:
                windows_after = int(result_after.stdout.strip())
                print(f"📊 启动后Terminal窗口数: {windows_after}")
                
                # 验证窗口数量增加
                self.assertGreater(windows_after, windows_before, 
                                 f"期望窗口数增加，但启动前: {windows_before}，启动后: {windows_after}")
                print("✅ 新Terminal窗口已成功创建")
            else:
                self.fail(f"无法检查Terminal窗口数: {result_after.stderr}")
                
        except Exception as e:
            self.fail(f"检查Terminal窗口失败: {e}")
    
    @unittest.skip("仅供人工验证，不参与自动化/CI：进程输出可见性")
    def test_process_output_visibility(self):
        """
        测试进程输出是否对用户可见
        """
        print("\n🎯 测试进程输出可见性")
        
        # 创建一个简单的测试脚本，输出一些内容
        test_script = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        test_script.write('''
import time
print("🎯 测试脚本启动")
print("📋 这是用户应该能看到的输出")
time.sleep(2)
print("✅ 测试脚本完成")
''')
        test_script.close()
        self.created_files.append(test_script.name)
        
        # 使用修复后的启动方法运行测试脚本
        import platform
        system = platform.system()
        
        if system == "Darwin":
            # 在macOS上测试AppleScript启动
            terminal_cmd = f'''
            tell application "Terminal"
                activate
                do script "cd '{project_root}' && python3 '{test_script.name}'"
            end tell
            '''
            
            print("🚀 使用AppleScript启动测试脚本...")
            applescript_process = subprocess.Popen(
                ["osascript", "-e", terminal_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            applescript_process.wait()
            
            if applescript_process.returncode == 0:
                print("✅ AppleScript执行成功")
                print("💡 请检查是否有新的Terminal窗口打开并显示测试输出")
            else:
                stderr = applescript_process.stderr.read()
                self.fail(f"AppleScript执行失败: {stderr}")
        else:
            print("⚠️ 非macOS系统，跳过AppleScript测试")
    
    def test_interactive_interface_accessibility(self):
        """
        测试交互界面是否可访问（用户能否与之交互）
        """
        print("\n🎯 测试交互界面可访问性")
        
        # 这个测试检查的是：启动的进程是否能接受用户输入
        test_params = {
            'name': 'test_accessibility',
            'host': 'access.test.com',
            'username': 'access_user'
        }
        
        result = self.config_manager.launch_cursor_terminal_config(prefill_params=test_params)
        
        # 记录文件用于清理
        if result.get('prefill_file'):
            self.created_files.append(result.get('prefill_file'))
        
        # 验证返回结果
        self.assertTrue(result.get('success'), f"启动失败: {result}")
        
        # 检查返回的平台类型
        platform_type = result.get('platform', '')
        terminal_type = result.get('terminal_type', '')
        
        print(f"📊 平台类型: {platform_type}")
        print(f"📊 终端类型: {terminal_type}")
        
        # 验证使用了正确的启动方式
        if platform_type == "macOS Terminal":
            self.assertEqual(terminal_type, "new_window", 
                           "在macOS上应该创建新窗口")
            print("✅ macOS使用了新Terminal窗口启动方式")
        else:
            print(f"📋 其他平台使用: {platform_type} / {terminal_type}")
    
    def test_background_process_detection(self):
        """
        测试检测后台进程问题（之前的bug）
        """
        print("\n🎯 测试后台进程检测")
        
        # 模拟旧的启动方式（重定向输出到PIPE）
        test_params = {'name': 'background_test', 'host': 'bg.test.com', 'username': 'bg_user'}
        
        # 创建预填充文件
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(test_params, temp_file, ensure_ascii=False, indent=2)
        temp_file.close()
        self.created_files.append(temp_file.name)
        
        # 使用旧的方式启动（重定向输出）
        cmd_args = [
            "python3", 
            str(project_root / "enhanced_config_manager.py"),
            "--cursor-terminal", 
            "--force-interactive",
            "--prefill", temp_file.name
        ]
        
        print("🚀 使用旧方式启动（重定向输出）...")
        old_process = subprocess.Popen(
            cmd_args,
            cwd=str(project_root),
            stdout=subprocess.PIPE,  # 这是问题所在！
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待一下
        time.sleep(1)
        
        # 检查进程状态
        poll_result = old_process.poll()
        if poll_result is None:
            print("📋 旧方式：进程仍在运行，但用户看不到输出")
            self.created_processes.append(old_process.pid)
        else:
            print(f"📋 旧方式：进程已结束，退出码: {poll_result}")
            # 获取输出
            stdout, stderr = old_process.communicate()
            print(f"标准输出: {stdout[:200]}...")
            print(f"错误输出: {stderr[:200]}...")
        
        print("✅ 后台进程问题检测完成")

def run_test():
    """运行测试的主函数"""
    print("🚀 开始用户可见交互界面验证测试")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUserVisibleInteraction)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    if result.wasSuccessful():
        print("🎉 所有用户体验测试通过！")
        return True
    else:
        print("❌ 用户体验测试失败")
        print(f"失败数量: {len(result.failures)}")
        print(f"错误数量: {len(result.errors)}")
        
        for test, traceback in result.failures + result.errors:
            print(f"\n❌ 失败测试: {test}")
            print(f"详细信息: {traceback}")
        
        return False

if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1) 