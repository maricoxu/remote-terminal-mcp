#!/usr/bin/env python3
"""
简单的MCP服务器测试
"""

import json
import subprocess
import sys
import os
import time

def test_mcp_server_basic():
    """测试MCP服务器基本功能"""
    
    # 设置环境变量
    env = os.environ.copy()
    env['NO_COLOR'] = '1'
    env['MCP_MODE'] = '1'
    
    print("🧪 启动MCP服务器...")
    
    try:
        # 启动MCP服务器
        proc = subprocess.Popen(
            [sys.executable, 'python/mcp_server.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # 发送简单的工具列表请求
        request = {
            "jsonrpc": "2.0",
            "id": "test_1",
            "method": "tools/list"
        }
        
        request_json = json.dumps(request) + "\n"
        print(f"📤 发送请求: {request['method']}")
        
        # 设置较短的超时时间
        try:
            stdout, stderr = proc.communicate(input=request_json, timeout=5)
            
            print(f"📥 收到响应长度: {len(stdout)} 字符")
            
            if stderr:
                print(f"⚠️ 错误输出: {stderr[:200]}...")
            
            if stdout:
                try:
                    response = json.loads(stdout.strip())
                    print("✅ JSON解析成功！")
                    
                    if "result" in response and "tools" in response["result"]:
                        tools_count = len(response["result"]["tools"])
                        print(f"✅ 发现 {tools_count} 个工具")
                        
                        # 显示前几个工具名称
                        tool_names = [tool["name"] for tool in response["result"]["tools"][:5]]
                        print(f"📋 工具示例: {', '.join(tool_names)}")
                        
                        return True
                    else:
                        print("❌ 响应格式异常")
                        return False
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {e}")
                    print(f"原始输出前200字符: {stdout[:200]}")
                    return False
            else:
                print("❌ 没有收到响应")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ 测试超时")
            proc.kill()
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_create_server_direct():
    """直接测试create_server_config工具"""
    
    env = os.environ.copy()
    env['NO_COLOR'] = '1'
    env['MCP_MODE'] = '1'
    
    print("\n🧪 测试create_server_config工具...")
    
    request = {
        "jsonrpc": "2.0",
        "id": "test_2",
        "method": "tools/call",
        "params": {
            "name": "create_server_config",
            "arguments": {
                "name": "test-server",
                "host": "192.168.1.100",
                "username": "testuser",
                "port": 22,
                "connection_type": "ssh",
                "description": "测试服务器"
            }
        }
    }
    
    try:
        proc = subprocess.Popen(
            [sys.executable, 'python/mcp_server.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        request_json = json.dumps(request) + "\n"
        print(f"📤 发送请求: {request['params']['name']}")
        
        stdout, stderr = proc.communicate(input=request_json, timeout=5)
        
        if stderr:
            print(f"⚠️ 错误输出: {stderr[:200]}...")
        
        if stdout:
            try:
                response = json.loads(stdout.strip())
                print("✅ JSON解析成功！")
                
                if "result" in response:
                    content = response["result"]["content"][0]["text"]
                    if "服务器配置创建成功" in content:
                        print("✅ 服务器配置创建成功")
                        return True
                    else:
                        print(f"⚠️ 意外的响应内容: {content[:100]}...")
                        return False
                        
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                return False
        else:
            print("❌ 没有收到响应")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 测试超时")
        proc.kill()
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始简单MCP服务器测试\n")
    
    # 切换到项目目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    test1_passed = test_mcp_server_basic()
    test2_passed = test_create_server_direct()
    
    print(f"\n📊 测试结果:")
    print(f"  基本功能测试: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"  创建服务器配置: {'✅ 通过' if test2_passed else '❌ 失败'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 所有测试通过！MCP服务器工作正常！")
        sys.exit(0)
    else:
        print("\n💔 部分测试失败，需要进一步调试")
        sys.exit(1) 