#!/usr/bin/env python3

import json
import subprocess
import sys
import time
import os

def test_mcp_server():
    print("🔍 Remote Terminal MCP 最终测试")
    print("=" * 50)
    
    # 等待NPM传播
    print("⏳ 等待NPM包传播...")
    time.sleep(5)
    
    # 强制清理缓存
    print("🧹 清理NPX缓存...")
    subprocess.run(['npx', 'clear-npx-cache'], capture_output=True)
    
    print("🚀 启动MCP服务器测试...")
    
    # 设置调试环境
    env = os.environ.copy()
    env['MCP_DEBUG'] = '1'
    
    # 启动MCP服务器
    process = subprocess.Popen(
        ['npx', '-y', '@xuyehua/remote-terminal-mcp@0.2.9'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    try:
        # 测试1: Initialize
        print("\n📤 测试1: Initialize请求")
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        process.stdin.write(json.dumps(initialize_request) + '\n')
        process.stdin.flush()
        
        # 读取响应
        response_line = process.stdout.readline()
        print(f"📥 Initialize响应: {response_line.strip()}")
        
        if response_line.strip():
            try:
                response = json.loads(response_line.strip())
                if response.get('result'):
                    print("✅ Initialize成功!")
                    server_info = response['result'].get('serverInfo', {})
                    print(f"   服务器: {server_info.get('name')}")
                    print(f"   版本: {server_info.get('version')}")
                else:
                    print("❌ Initialize失败")
                    return False
            except Exception as e:
                print(f"❌ Initialize响应解析失败: {e}")
                return False
        else:
            print("❌ 没有收到Initialize响应")
            return False
        
        # 测试2: Tools List
        print("\n📤 测试2: Tools/List请求")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        process.stdin.write(json.dumps(tools_request) + '\n')
        process.stdin.flush()
        
        # 读取工具列表响应
        tools_response_line = process.stdout.readline()
        print(f"📥 Tools响应: {tools_response_line.strip()[:200]}...")
        
        if tools_response_line.strip():
            try:
                tools_response = json.loads(tools_response_line.strip())
                tools = tools_response.get('result', {}).get('tools', [])
                print(f"✅ 找到 {len(tools)} 个工具!")
                
                expected_tools = [
                    'system_info', 'run_command', 'list_tmux_sessions', 
                    'create_tmux_session', 'list_directory', 'list_remote_servers',
                    'test_server_connection', 'execute_remote_command', 
                    'get_server_status', 'refresh_server_connections', 'establish_connection'
                ]
                
                found_tools = [tool.get('name') for tool in tools]
                print("   工具列表:")
                for tool_name in found_tools:
                    status = "✅" if tool_name in expected_tools else "⚠️"
                    print(f"   {status} {tool_name}")
                
                if len(tools) >= 10:
                    print("✅ 工具数量正常!")
                    return True
                else:
                    print(f"❌ 工具数量不足: {len(tools)}/11")
                    return False
                    
            except Exception as e:
                print(f"❌ 工具列表响应解析失败: {e}")
                return False
        else:
            print("❌ 没有收到工具列表响应")
            return False
            
    finally:
        print("\n🛑 终止MCP服务器...")
        process.terminate()
        
        # 等待进程结束并获取stderr
        try:
            stdout, stderr = process.communicate(timeout=5)
            if stderr:
                print("\n📝 调试日志:")
                print("-" * 30)
                print(stderr)
                print("-" * 30)
        except subprocess.TimeoutExpired:
            process.kill()

def main():
    success = test_mcp_server()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 MCP服务器测试成功!")
        print("\n📋 下一步操作:")
        print("1. 重启Cursor")
        print("2. 检查Cursor MCP工具面板")
        print("3. 应该看到11个remote-terminal工具")
        print("\n💡 如果还是显示0个工具，请:")
        print("- 确认 ~/.cursor/mcp.json 配置正确")
        print("- 重启Cursor应用")
        print("- 检查Cursor MCP日志")
    else:
        print("❌ MCP服务器测试失败!")
        print("请检查错误信息并重试")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 