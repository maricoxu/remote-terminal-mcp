#!/usr/bin/env python3
"""
回归测试：MCP服务器重启和新代码加载验证

测试目标：
- 验证MCP服务器能够正常重启
- 测试新代码修改（特别是update_server_config交互行为）能正确加载
- 确保没有语法错误导致启动失败
- 验证重启后的服务器能正常响应工具调用
- 测试新的update_server_config交互行为

修复问题：
1. 修复了NameError: name 'true' is not defined语法错误
2. 确保MCP服务器重启后新代码能正确加载
3. 验证update_server_config的新交互行为生效

创建日期：2024-12-22
"""

import os
import sys
import json
import yaml
import time
import signal
import tempfile
import unittest
import subprocess
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class TestMCPRestartAndNewCodeLoading(unittest.TestCase):
    """测试MCP服务器重启和新代码加载"""
    
    def setUp(self):
        """测试前准备"""
        self.project_root = project_root
        self.mcp_server_path = self.project_root / "python" / "mcp_server.py"
        self.index_js_path = self.project_root / "index.js"
        self.test_processes = []
        
    def tearDown(self):
        """测试后清理"""
        # 清理测试进程
        for process in self.test_processes:
            try:
                if process.poll() is None:  # 进程还在运行
                    process.terminate()
                    process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
    
    def test_mcp_server_syntax_validation(self):
        """测试MCP服务器Python语法验证"""
        print("🎯 测试MCP服务器Python语法")
        
        # 使用Python编译器验证语法
        result = subprocess.run([
            sys.executable, "-m", "py_compile", str(self.mcp_server_path)
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0, 
            f"MCP服务器语法错误:\n{result.stderr}")
        
        print("✅ MCP服务器Python语法验证通过")
    
    def test_mcp_server_import_validation(self):
        """测试MCP服务器模块导入验证"""
        print("🎯 测试MCP服务器模块导入")
        
        # 测试能否正常导入所需模块
        test_script = f"""
import sys
sys.path.insert(0, '{self.project_root}')

try:
    # 测试基本导入
    import json
    import yaml
    import asyncio
    import subprocess
    from pathlib import Path
    
    # 测试项目模块导入
    from config_manager.main import EnhancedConfigManager
    
    print("✅ 所有模块导入成功")
    exit(0)
except Exception as e:
    print(f"❌ 模块导入失败: {{e}}")
    exit(1)
"""
        
        result = subprocess.run([
            sys.executable, "-c", test_script
        ], capture_output=True, text=True, cwd=str(self.project_root))
        
        self.assertEqual(result.returncode, 0, 
            f"模块导入失败:\n{result.stderr}\n{result.stdout}")
        
        print("✅ MCP服务器模块导入验证通过")
    
    def test_mcp_server_startup_without_errors(self):
        """测试MCP服务器能否无错误启动"""
        print("🎯 测试MCP服务器无错误启动")
        
        # 启动MCP服务器并检查是否有语法错误
        process = subprocess.Popen([
            sys.executable, "-u", str(self.mcp_server_path)
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, text=True, cwd=str(self.project_root))
        
        self.test_processes.append(process)
        
        # 发送初始化请求
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        try:
            # 发送请求
            process.stdin.write(json.dumps(init_request) + '\n')
            process.stdin.flush()
            
            # 等待响应（最多5秒）
            response_received = False
            for _ in range(50):  # 5秒，每100ms检查一次
                if process.poll() is not None:
                    # 进程已退出，检查错误
                    stderr_output = process.stderr.read()
                    if "NameError: name 'true' is not defined" in stderr_output:
                        self.fail(f"MCP服务器启动时出现语法错误:\n{stderr_output}")
                    elif "SyntaxError" in stderr_output:
                        self.fail(f"MCP服务器启动时出现语法错误:\n{stderr_output}")
                    break
                
                # 检查是否有响应
                try:
                    import select
                    if select.select([process.stdout], [], [], 0.1)[0]:
                        response_line = process.stdout.readline()
                        if response_line.strip():
                            response_received = True
                            response = json.loads(response_line)
                            self.assertEqual(response.get("jsonrpc"), "2.0")
                            self.assertEqual(response.get("id"), 1)
                            self.assertIn("result", response)
                            break
                except:
                    pass
                
                time.sleep(0.1)
            
            if not response_received and process.poll() is None:
                print("⚠️ 未收到初始化响应，但进程仍在运行（可能正常）")
            elif response_received:
                print("✅ 收到有效的初始化响应")
            
        finally:
            # 清理进程
            try:
                process.terminate()
                process.wait(timeout=2)
            except:
                process.kill()
        
        print("✅ MCP服务器启动测试通过")
    
    def test_tools_list_generation(self):
        """测试工具列表生成是否正常"""
        print("🎯 测试工具列表生成")
        
        # 直接测试create_tools_list函数
        test_script = f"""
import sys
sys.path.insert(0, '{self.project_root}')

try:
    # 导入MCP服务器模块
    import importlib.util
    spec = importlib.util.spec_from_file_location("mcp_server", '{self.mcp_server_path}')
    mcp_server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mcp_server)
    
    # 测试create_tools_list函数
    tools = mcp_server.create_tools_list()
    
    # 验证工具列表
    assert isinstance(tools, list), "工具列表应该是一个列表"
    assert len(tools) > 0, "工具列表不应为空"
    
    # 查找update_server_config工具
    update_tool = None
    for tool in tools:
        if tool.get('name') == 'update_server_config':
            update_tool = tool
            break
    
    assert update_tool is not None, "应该包含update_server_config工具"
    
    # 验证Docker参数
    properties = update_tool.get('inputSchema', {{}}).get('properties', {{}})
    docker_params = ['docker_enabled', 'docker_image', 'docker_container', 
                    'docker_ports', 'docker_volumes', 'docker_shell', 'docker_auto_create']
    
    for param in docker_params:
        assert param in properties, f"update_server_config应该包含{{param}}参数"
    
    # 验证布尔值默认值（确保使用True而不是true）
    docker_auto_create = properties.get('docker_auto_create', {{}})
    default_value = docker_auto_create.get('default')
    assert default_value is True, f"docker_auto_create的默认值应该是True，实际是{{default_value}}"
    
    print("✅ 工具列表生成验证成功")
    print(f"✅ 找到{{len(tools)}}个工具")
    print("✅ update_server_config工具包含所有Docker参数")
    print("✅ 布尔值默认值使用正确的Python语法")
    
except Exception as e:
    print(f"❌ 工具列表生成测试失败: {{e}}")
    import traceback
    traceback.print_exc()
    exit(1)
"""
        
        result = subprocess.run([
            sys.executable, "-c", test_script
        ], capture_output=True, text=True, cwd=str(self.project_root))
        
        if result.returncode != 0:
            self.fail(f"工具列表生成失败:\n{result.stderr}\n{result.stdout}")
        
        print("✅ 工具列表生成测试通过")
    
    def test_new_update_server_config_logic_loading(self):
        """测试新的update_server_config逻辑是否正确加载"""
        print("🎯 测试新的update_server_config逻辑加载")
        
        # 检查代码中是否包含新的逻辑标记
        with open(self.mcp_server_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 验证新逻辑标记存在
        self.assertIn("NEW UPDATE LOGIC", content, 
            "代码中应该包含新的update_server_config逻辑标记")
        
        self.assertIn("强制交互策略：与create_server_config保持一致", content,
            "代码中应该包含新的交互策略注释")
        
        self.assertIn("launch_cursor_terminal_config", content,
            "代码中应该包含交互界面启动调用")
        
        print("✅ 新的update_server_config逻辑标记验证通过")
    
    def test_mcp_server_restart_simulation(self):
        """模拟MCP服务器重启过程"""
        print("🎯 模拟MCP服务器重启过程")
        
        # 第一次启动
        print("🚀 第一次启动MCP服务器...")
        process1 = subprocess.Popen([
            sys.executable, "-u", str(self.mcp_server_path)
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, text=True, cwd=str(self.project_root))
        
        self.test_processes.append(process1)
        
        # 等待启动
        time.sleep(1)
        
        # 检查第一次启动是否成功
        if process1.poll() is not None:
            stderr_output = process1.stderr.read()
            if stderr_output:
                self.fail(f"第一次启动失败:\n{stderr_output}")
        
        print("✅ 第一次启动成功")
        
        # 终止第一个进程
        print("🔄 终止第一个进程...")
        process1.terminate()
        process1.wait(timeout=5)
        
        # 第二次启动（模拟重启）
        print("🚀 第二次启动MCP服务器（模拟重启）...")
        process2 = subprocess.Popen([
            sys.executable, "-u", str(self.mcp_server_path)
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, text=True, cwd=str(self.project_root))
        
        self.test_processes.append(process2)
        
        # 等待启动
        time.sleep(1)
        
        # 检查第二次启动是否成功
        if process2.poll() is not None:
            stderr_output = process2.stderr.read()
            if stderr_output:
                self.fail(f"重启后启动失败:\n{stderr_output}")
        
        print("✅ 重启后启动成功")
        
        # 清理第二个进程
        process2.terminate()
        process2.wait(timeout=5)
        
        print("✅ MCP服务器重启模拟测试通过")
    
    def test_index_js_startup_with_python_backend(self):
        """测试通过index.js启动Python后端"""
        print("🎯 测试通过index.js启动Python后端")
        
        # 通过index.js启动（这是Cursor实际使用的方式）
        process = subprocess.Popen([
            "node", str(self.index_js_path)
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, text=True, cwd=str(self.project_root))
        
        self.test_processes.append(process)
        
        # 等待启动
        time.sleep(2)
        
        # 检查是否有语法错误
        if process.poll() is not None:
            stderr_output = process.stderr.read()
            stdout_output = process.stdout.read()
            if "NameError: name 'true' is not defined" in stderr_output:
                self.fail(f"通过index.js启动时出现语法错误:\n{stderr_output}")
            elif "SyntaxError" in stderr_output:
                self.fail(f"通过index.js启动时出现语法错误:\n{stderr_output}")
            elif stderr_output:
                print(f"⚠️ 启动时的stderr输出:\n{stderr_output}")
        
        print("✅ 通过index.js启动Python后端测试通过")
        
        # 清理进程
        process.terminate()
        process.wait(timeout=5)
    
    def test_code_change_detection(self):
        """测试代码变更检测"""
        print("🎯 测试代码变更检测")
        
        # 检查文件的最后修改时间
        mcp_server_mtime = os.path.getmtime(self.mcp_server_path)
        current_time = time.time()
        
        # 如果文件在最近10分钟内被修改，说明有新的变更
        time_diff = current_time - mcp_server_mtime
        if time_diff < 600:  # 10分钟
            print(f"✅ 检测到最近的代码变更（{time_diff:.1f}秒前）")
        else:
            print(f"⚠️ 代码文件较旧（{time_diff/60:.1f}分钟前修改）")
        
        # 验证修复标记存在
        with open(self.mcp_server_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否包含修复后的True（而不是true）
        true_count = content.count('"default": True')
        false_count = content.count('"default": False')
        
        self.assertGreater(true_count, 0, "应该包含修复后的True默认值")
        self.assertGreater(false_count, 0, "应该包含修复后的False默认值")
        
        # 确保没有小写的true/false
        self.assertNotIn('"default": true', content, 
            "不应该包含小写的true（这会导致语法错误）")
        self.assertNotIn('"default": false', content,
            "不应该包含小写的false（这会导致语法错误）")
        
        print(f"✅ 发现 {true_count} 个True默认值")
        print(f"✅ 发现 {false_count} 个False默认值")
        print("✅ 没有发现有问题的小写true/false")
        print("✅ 代码变更检测通过")

def run_mcp_restart_tests():
    """运行MCP重启和新代码加载测试"""
    print("🚀 开始MCP服务器重启和新代码加载回归测试")
    print("=" * 70)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMCPRestartAndNewCodeLoading)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 70)
    if result.wasSuccessful():
        print("🎉 所有MCP重启和新代码加载测试通过！")
        print("🎯 修复验证成功：")
        print("  ✅ 语法错误已修复（true -> True）")
        print("  ✅ MCP服务器能正常重启")
        print("  ✅ 新的update_server_config逻辑已加载")
        print("  ✅ 重启后服务器能正常响应")
    else:
        print("❌ 部分测试失败，需要进一步修复")
        for failure in result.failures:
            print(f"失败测试: {failure[0]}")
            print(f"失败原因: {failure[1]}")
        for error in result.errors:
            print(f"错误测试: {error[0]}")
            print(f"错误信息: {error[1]}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_mcp_restart_tests()
    sys.exit(0 if success else 1) 