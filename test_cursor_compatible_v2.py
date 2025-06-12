#!/usr/bin/env python3

import subprocess
import json
import os
import time

def test_mcp_server():
    print("🚀 开始测试 Cursor 兼容的 MCP 服务器...")
    
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
            print(f"📤 发送请求: {request['method']}")
            process.stdin.write(request_line)
            process.stdin.flush()
            
            # 使用缓冲读取代替readline
            response_data = ""
            start_time = time.time()
            timeout = 10  # 10秒超时
            
            while True:
                # 检查超时
                if time.time() - start_time > timeout:
                    print(f"⏰ 读取响应超时 ({timeout}秒)")
                    return None
                
                # 检查进程是否还在运行
                if process.poll() is not None:
                    print("❌ MCP服务器进程已退出")
                    return None
                
                # 尝试读取一个字符
                try:
                    char = process.stdout.read(1)
                    if not char:
                        time.sleep(0.01)  # 短暂等待
                        continue
                    
                    response_data += char
                    
                    # 检查是否是完整的JSON行
                    if char == '\n':
                        try:
                            response = json.loads(response_data.strip())
                            print(f"📥 收到响应 ({len(response_data)} 字符)")
                            return response
                        except json.JSONDecodeError:
                            # 可能是多行JSON，继续读取
                            continue
                    
                except Exception as e:
                    print(f"❌ 读取响应时出错: {e}")
                    return None
        
        except Exception as e:
            print(f"❌ 发送请求时出错: {e}")
            return None
    
    try:
        # 1. 测试初始化
        print("\n=== 1. 测试初始化 ===")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {}
            }
        }
        
        response = send_request_and_read_response(init_request)
        if response:
            print("✅ 初始化成功")
            print(f"   服务器信息: {response.get('result', {}).get('serverInfo', {})}")
        else:
            print("❌ 初始化失败")
            return
        
        # 2. 测试工具列表
        print("\n=== 2. 测试工具列表 ===")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        response = send_request_and_read_response(tools_request)
        if response and 'result' in response:
            tools = response['result'].get('tools', [])
            print(f"✅ 获取到 {len(tools)} 个工具:")
            for tool in tools:
                print(f"   - {tool.get('name')}: {tool.get('description')}")
        else:
            print("❌ 获取工具列表失败")
            return
        
        # 3. 测试list_servers工具
        print("\n=== 3. 测试 list_servers 工具 ===")
        list_servers_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "list_servers",
                "arguments": {}
            }
        }
        
        response = send_request_and_read_response(list_servers_request)
        if response and 'result' in response:
            content = response['result'].get('content', [])
            if content:
                server_data = content[0].get('text', '')
                print(f"✅ 获取服务器列表成功 ({len(server_data)} 字符)")
                try:
                    servers = json.loads(server_data)
                    print(f"   解析到 {len(servers)} 个服务器:")
                    for server in servers[:3]:  # 只显示前3个
                        print(f"   - {server.get('name')}: {server.get('description')}")
                    if len(servers) > 3:
                        print(f"   ... 还有 {len(servers) - 3} 个服务器")
                except:
                    print(f"   原始数据: {server_data[:200]}...")
            else:
                print("❌ 没有收到服务器数据")
        else:
            print("❌ 调用 list_servers 失败")
        
        print("\n🎉 测试完成！")
        
    finally:
        # 清理进程
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()

if __name__ == "__main__":
    test_mcp_server() 