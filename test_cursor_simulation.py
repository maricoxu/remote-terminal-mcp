#!/usr/bin/env python3
"""
模拟Cursor客户端的具体行为测试
基于实际日志分析Cursor的请求序列
"""

import subprocess
import json
import sys
import time
import threading
import os
from pathlib import Path

class CursorSimulator:
    def __init__(self, service_path):
        self.service_path = service_path
        self.process = None
        self.responses = []
        
    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [CURSOR-SIM] {message}")
        
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
            
            # 启动监听线程
            self.output_thread = threading.Thread(target=self._monitor_responses)
            self.output_thread.daemon = True
            self.output_thread.start()
            
            self.error_thread = threading.Thread(target=self._monitor_errors)
            self.error_thread.daemon = True
            self.error_thread.start()
            
            time.sleep(1)
            return True
            
        except Exception as e:
            self.log(f"启动服务失败: {e}")
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
                        self.log(f"收到响应: {json.dumps(response, ensure_ascii=False)}")
                    except json.JSONDecodeError:
                        self.log(f"无法解析响应: {line}")
            except Exception as e:
                break
                
    def _monitor_errors(self):
        """监听错误输出但不打印（减少噪音）"""
        while self.process and self.process.poll() is None:
            try:
                line = self.process.stderr.readline()
                if line and "ERROR" in line.upper():
                    self.log(f"[ERROR] {line.strip()}")
            except Exception:
                break
    
    def send_request_and_wait(self, request_obj, timeout=3):
        """发送请求并等待特定响应"""
        if not self.process:
            return None
            
        request_id = request_obj.get("id")
        request_json = json.dumps(request_obj)
        self.log(f"发送请求: {request_obj['method']} (ID: {request_id})")
        
        # 清除之前的响应
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
            # 检查是否有新响应
            if len(self.responses) > initial_response_count:
                for response in self.responses[initial_response_count:]:
                    if response.get("id") == request_id:
                        return response
            time.sleep(0.1)
        
        self.log(f"请求 {request_id} 超时")
        return None
    
    def simulate_cursor_handshake(self):
        """模拟Cursor的完整握手序列"""
        self.log("=== 开始Cursor握手模拟 ===")
        
        # 1. Initialize请求 (这是标准的)
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
                    "name": "cursor",
                    "version": "0.44.9"
                }
            }
        }
        
        init_response = self.send_request_and_wait(init_request)
        if not init_response:
            self.log("❌ Initialize失败")
            return False
        
        if "error" in init_response:
            self.log(f"❌ Initialize错误: {init_response['error']}")
            return False
            
        self.log("✅ Initialize成功")
        
        # 2. 检查是否需要发送initialized通知
        self.log("发送initialized通知...")
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
        
        # 3. ListOfferings请求 (这是Cursor特有的)
        offerings_request = {
            "jsonrpc": "2.0",
            "id": "1", 
            "method": "ListOfferings",
            "params": {}
        }
        
        offerings_response = self.send_request_and_wait(offerings_request)
        if not offerings_response:
            self.log("❌ ListOfferings失败或超时")
            return False
            
        if "error" in offerings_response:
            self.log(f"❌ ListOfferings错误: {offerings_response['error']}")
            return False
            
        self.log("✅ ListOfferings成功")
        
        # 4. 尝试tools/list
        tools_request = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/list", 
            "params": {}
        }
        
        tools_response = self.send_request_and_wait(tools_request)
        if tools_response:
            self.log("✅ tools/list成功")
        else:
            self.log("❌ tools/list失败")
        
        self.log("=== 握手完成 ===")
        return True
    
    def stop_service(self):
        if self.process:
            self.process.terminate()
            self.process.wait()

def main():
    service_path = Path(__file__).parent / "bin" / "cli.js"
    
    if not service_path.exists():
        print(f"错误: 找不到服务文件 {service_path}")
        sys.exit(1)
    
    simulator = CursorSimulator(str(service_path))
    
    try:
        if simulator.start_service():
            success = simulator.simulate_cursor_handshake()
            if success:
                print("\n🎉 模拟成功！服务应该能在Cursor中正常工作")
            else:
                print("\n❌ 模拟失败，需要进一步调试")
        else:
            print("❌ 服务启动失败")
    except KeyboardInterrupt:
        print("\n测试被中断")
    finally:
        simulator.stop_service()

if __name__ == "__main__":
    main() 