#!/usr/bin/env python3
"""
NPM版本MCP服务测试脚本
专门用于测试通过npx安装的@xuyehua/remote-terminal-mcp包
"""

import subprocess
import json
import sys
import time
import threading
import os
from pathlib import Path

class NPMVersionTester:
    def __init__(self, version="0.5.0"):
        self.version = version
        self.package_name = f"@xuyehua/remote-terminal-mcp@{version}"
        self.process = None
        self.responses = []
        
    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [NPM-TEST] {message}")
        
    def start_service(self):
        """启动NPM版本的MCP服务"""
        self.log(f"启动NPM版本: {self.package_name}")
        
        try:
            # 使用npx启动服务，就像Cursor一样
            self.process = subprocess.Popen(
                ["npx", "-y", self.package_name],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0
            )
            self.log(f"NPM服务进程已启动，PID: {self.process.pid}")
            
            # 启动监听线程
            self.output_thread = threading.Thread(target=self._monitor_responses)
            self.output_thread.daemon = True
            self.output_thread.start()
            
            self.error_thread = threading.Thread(target=self._monitor_errors)
            self.error_thread.daemon = True
            self.error_thread.start()
            
            time.sleep(3)  # NPM版本可能需要更长的启动时间
            return True
            
        except Exception as e:
            self.log(f"启动NPM服务失败: {e}")
            return False
    
    def _monitor_responses(self):
        """监听并解析响应"""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if line:
                    line = line.strip()
                    try:
                        response = json.loads(line)
                        self.responses.append(response)
                        self.log(f"收到响应: {response.get('id', 'N/A')} - {response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")
                    except json.JSONDecodeError:
                        if line and not line.startswith('['):  # 忽略调试日志
                            self.log(f"非JSON响应: {line}")
            except Exception as e:
                break
                
    def _monitor_errors(self):
        """监听错误输出"""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stderr.readline()
                if line:
                    line = line.strip()
                    if "ERROR" in line.upper() or "FATAL" in line.upper():
                        self.log(f"[ERROR] {line}")
                    elif "Starting MCP Python Server" in line:
                        self.log(f"[INFO] {line}")
            except Exception:
                break
    
    def send_request_and_wait(self, request_obj, timeout=5):
        """发送请求并等待响应"""
        if not self.process:
            return None
            
        request_id = request_obj.get("id")
        request_json = json.dumps(request_obj)
        self.log(f"发送请求: {request_obj['method']} (ID: {request_id})")
        
        initial_response_count = len(self.responses)
        
        try:
            self.process.stdin.write(request_json + "\n")
            self.process.stdin.flush()
        except Exception as e:
            self.log(f"发送失败: {e}")
            return None
        
        # 等待响应
        start_time = time.time()
        while time.time() - start_time < timeout:
            if len(self.responses) > initial_response_count:
                for response in self.responses[initial_response_count:]:
                    if response.get("id") == request_id:
                        return response
            time.sleep(0.1)
        
        self.log(f"请求 {request_id} 超时")
        return None
    
    def test_npm_version(self):
        """测试NPM版本的完整功能"""
        self.log("=== 开始NPM版本测试 ===")
        
        # 1. Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": "0",
            "method": "initialize",
            "params": {
                "capabilities": {
                    "tools": {},
                    "resources": {}
                },
                "clientInfo": {
                    "name": "npm-test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        init_response = self.send_request_and_wait(init_request)
        if not init_response or "error" in init_response:
            self.log("❌ Initialize失败")
            return False
        
        # 检查版本信息
        server_info = init_response.get("result", {}).get("serverInfo", {})
        server_version = server_info.get("version", "Unknown")
        self.log(f"✅ Initialize成功 - 服务器版本: {server_version}")
        
        # 2. Initialized通知
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        try:
            request_json = json.dumps(initialized_notification)
            self.process.stdin.write(request_json + "\n")
            self.process.stdin.flush()
            time.sleep(0.5)
        except Exception as e:
            self.log(f"initialized通知发送失败: {e}")
        
        # 3. ListOfferings
        offerings_request = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "ListOfferings",
            "params": {}
        }
        
        offerings_response = self.send_request_and_wait(offerings_request)
        if offerings_response and "error" not in offerings_response:
            self.log("✅ ListOfferings成功")
        else:
            self.log("❌ ListOfferings失败")
            return False
        
        # 4. Tools/list
        tools_request = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/list",
            "params": {}
        }
        
        tools_response = self.send_request_and_wait(tools_request)
        if tools_response and "error" not in tools_response:
            tools = tools_response.get("result", {}).get("tools", [])
            self.log(f"✅ tools/list成功 - 发现 {len(tools)} 个工具")
            for tool in tools:
                self.log(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        else:
            self.log("❌ tools/list失败")
            return False
        
        # 5. 测试一个工具调用
        tool_call_request = {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "tools/call",
            "params": {
                "name": "list_servers",
                "arguments": {}
            }
        }
        
        tool_response = self.send_request_and_wait(tool_call_request)
        if tool_response and "error" not in tool_response:
            self.log("✅ 工具调用成功")
        else:
            self.log("❌ 工具调用失败")
            if tool_response and "error" in tool_response:
                self.log(f"错误详情: {tool_response['error']}")
        
        self.log("=== NPM版本测试完成 ===")
        return True
    
    def stop_service(self):
        if self.process:
            self.process.terminate()
            self.process.wait()

def main():
    tester = NPMVersionTester("0.5.1")
    
    try:
        if tester.start_service():
            success = tester.test_npm_version()
            if success:
                print("\n🎉 NPM版本测试成功！")
            else:
                print("\n❌ NPM版本测试失败")
        else:
            print("❌ NPM服务启动失败")
    except KeyboardInterrupt:
        print("\n测试被中断")
    finally:
        tester.stop_service()

if __name__ == "__main__":
    main() 