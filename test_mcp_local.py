#!/usr/bin/env python3
"""
本地MCP服务测试脚本 - 模拟Cursor客户端行为
用于快速迭代调试MCP服务，避免每次都要重启Cursor
"""

import subprocess
import json
import sys
import time
import threading
import os
from pathlib import Path

class MCPTester:
    def __init__(self, service_path):
        self.service_path = service_path
        self.process = None
        self.output_lines = []
        
    def log(self, message):
        """记录测试日志"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [TEST] {message}")
        
    def start_service(self):
        """启动MCP服务"""
        self.log(f"启动MCP服务: {self.service_path}")
        
        try:
            self.process = subprocess.Popen(
                ["node", self.service_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            self.log(f"服务进程已启动，PID: {self.process.pid}")
            
            # 启动输出监听线程
            self.output_thread = threading.Thread(target=self._monitor_output)
            self.output_thread.daemon = True
            self.output_thread.start()
            
            # 启动错误监听线程  
            self.error_thread = threading.Thread(target=self._monitor_error)
            self.error_thread.daemon = True
            self.error_thread.start()
            
            time.sleep(1)  # 给服务一点启动时间
            return True
            
        except Exception as e:
            self.log(f"启动服务失败: {e}")
            return False
    
    def _monitor_output(self):
        """监听标准输出"""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    line = line.strip()
                    self.output_lines.append(line)
                    self.log(f"[STDOUT] {line}")
            except Exception as e:
                self.log(f"读取输出时出错: {e}")
                break
                
    def _monitor_error(self):
        """监听标准错误"""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stderr.readline()
                if line:
                    line = line.strip()
                    self.log(f"[STDERR] {line}")
            except Exception as e:
                self.log(f"读取错误输出时出错: {e}")
                break
    
    def send_request(self, request_obj):
        """发送JSON-RPC请求"""
        if not self.process:
            self.log("服务未启动")
            return None
            
        try:
            request_json = json.dumps(request_obj)
            self.log(f"发送请求: {request_json}")
            
            # 发送纯JSON（不带Content-Length头）
            self.process.stdin.write(request_json + "\n")
            self.process.stdin.flush()
            
            # 等待响应（通过监听输出）
            time.sleep(1)
            return True
            
        except Exception as e:
            self.log(f"发送请求失败: {e}")
            return False
    
    def test_initialize(self):
        """测试initialize请求"""
        self.log("=== 测试 Initialize 请求 ===")
        
        request = {
            "jsonrpc": "2.0",
            "id": "0",
            "method": "initialize",
            "params": {
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "clientInfo": {
                    "name": "cursor-test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        return self.send_request(request)
    
    def test_list_offerings(self):
        """测试ListOfferings请求"""
        self.log("=== 测试 ListOfferings 请求 ===")
        
        request = {
            "jsonrpc": "2.0", 
            "id": "1",
            "method": "ListOfferings",
            "params": {}
        }
        
        return self.send_request(request)
    
    def test_tools_list(self):
        """测试tools/list请求"""
        self.log("=== 测试 tools/list 请求 ===")
        
        request = {
            "jsonrpc": "2.0",
            "id": "2", 
            "method": "tools/list",
            "params": {}
        }
        
        return self.send_request(request)
    
    def test_tools_call(self):
        """测试tools/call请求"""
        self.log("=== 测试 tools/call 请求 ===")
        
        request = {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "tools/call",
            "params": {
                "name": "list_servers",
                "arguments": {}
            }
        }
        
        return self.send_request(request)
    
    def run_full_test(self):
        """运行完整测试套件"""
        self.log("开始完整的MCP服务测试")
        
        # 1. 启动服务
        if not self.start_service():
            self.log("服务启动失败，测试终止")
            return False
        
        # 2. 测试initialize（这是必须的握手步骤）
        time.sleep(2)
        if not self.test_initialize():
            self.log("Initialize测试失败")
        
        # 3. 测试ListOfferings
        time.sleep(2)
        if not self.test_list_offerings():
            self.log("ListOfferings测试失败")
        
        # 4. 测试tools/list
        time.sleep(2) 
        if not self.test_tools_list():
            self.log("tools/list测试失败")
        
        # 5. 测试tools/call
        time.sleep(2)
        if not self.test_tools_call():
            self.log("tools/call测试失败")
        
        # 等待一段时间收集所有响应
        self.log("等待响应...")
        time.sleep(3)
        
        self.log("测试完成")
        return True
    
    def stop_service(self):
        """停止服务"""
        if self.process:
            self.log("停止服务")
            self.process.terminate()
            self.process.wait()
            self.process = None

def main():
    # 使用当前项目的bin/cli.js
    service_path = Path(__file__).parent / "bin" / "cli.js"
    
    if not service_path.exists():
        print(f"错误: 找不到服务文件 {service_path}")
        sys.exit(1)
    
    tester = MCPTester(str(service_path))
    
    try:
        tester.run_full_test()
    except KeyboardInterrupt:
        tester.log("测试被用户中断")
    finally:
        tester.stop_service()

if __name__ == "__main__":
    main() 