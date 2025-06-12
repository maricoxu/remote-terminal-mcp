#!/usr/bin/env python3

import subprocess
import json
import os
import time

def test_cursor_protocol():
    print("🚀 测试真实的Cursor MCP协议...")
    
    # 设置环境变量
    env = os.environ.copy()
    env['MCP_QUIET'] = '1'
    
    # 启动MCP服务器
    process = subprocess.Popen(
        ['python3', 'python/mcp_server_debug.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd='.'
    )
    
    def send_request_and_read_response(request):
        """发送请求并读取完整响应"""
        try:
            # 发送请求
            request_line = json.dumps(request, ensure_ascii=False) + '\n'
            print(f"📤 发送: {request.get('method', 'notification')}")
            process.stdin.write(request_line)
            process.stdin.flush()
            
            # 对于通知，不期待响应
            if request.get('method') == 'notifications/initialized':
                print("📥 通知已发送，无需响应")
                time.sleep(0.1)  # 短暂等待处理完成
                return {"_notification": True}
            
            # 使用缓冲读取
            response_data = ""
            start_time = time.time()
            timeout = 10
            
            while True:
                if time.time() - start_time > timeout:
                    print(f"⏰ 读取响应超时 ({timeout}秒)")
                    return None
                
                if process.poll() is not None:
                    print("❌ MCP服务器进程已退出")
                    return None
                
                try:
                    char = process.stdout.read(1)
                    if not char:
                        time.sleep(0.01)
                        continue
                    
                    response_data += char
                    
                    if char == '\n':
                        try:
                            response = json.loads(response_data.strip())
                            print(f"📥 收到响应 ({len(response_data)} 字符)")
                            return response
                        except json.JSONDecodeError:
                            continue
                    
                except Exception as e:
                    print(f"❌ 读取响应时出错: {e}")
                    return None
        
        except Exception as e:
            print(f"❌ 发送请求时出错: {e}")
            return None
    
    try:
        # 1. 发送真实的Cursor初始化请求
        print("\n=== 1. Cursor初始化请求 ===")
        cursor_init = {
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "tools": True,
                    "prompts": False,
                    "resources": False,
                    "logging": False,
                    "roots": {"listChanged": False}
                },
                "clientInfo": {"name": "cursor-vscode", "version": "1.0.0"}
            },
            "jsonrpc": "2.0",
            "id": 0
        }
        
        response = send_request_and_read_response(cursor_init)
        if response and 'result' in response:
            server_info = response['result'].get('serverInfo', {})
            protocol_version = response['result'].get('protocolVersion', 'unknown')
            print(f"✅ 初始化成功")
            print(f"   服务器: {server_info.get('name')} v{server_info.get('version')}")
            print(f"   协议版本: {protocol_version}")
        else:
            print("❌ 初始化失败")
            return
        
        # 2. 发送通知
        print("\n=== 2. Cursor初始化完成通知 ===")
        cursor_notification = {
            "method": "notifications/initialized",
            "jsonrpc": "2.0"
        }
        
        response = send_request_and_read_response(cursor_notification)
        if response and response.get('_notification'):
            print("✅ 通知处理成功")
        else:
            print("❌ 通知处理失败")
        
        # 3. 获取工具列表
        print("\n=== 3. Cursor工具列表请求 ===")
        cursor_tools = {
            "method": "tools/list",
            "jsonrpc": "2.0",
            "id": 1
        }
        
        response = send_request_and_read_response(cursor_tools)
        if response and 'result' in response:
            tools = response['result'].get('tools', [])
            print(f"✅ 获取到 {len(tools)} 个工具:")
            for tool in tools:
                print(f"   - {tool.get('name')}: {tool.get('description')}")
        else:
            print("❌ 获取工具列表失败")
        
        print("\n🎉 Cursor协议测试完成！")
        
    finally:
        # 清理进程
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()

if __name__ == "__main__":
    test_cursor_protocol() 