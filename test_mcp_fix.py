#!/usr/bin/env python3
"""
测试MCP工具修复是否有效
"""

import json
import subprocess
import sys
import os

def test_mcp_interactive_config():
    """测试MCP交互式配置工具"""
    
    # 模拟MCP工具调用
    test_request = {
        "jsonrpc": "2.0",
        "id": "test_1",
        "method": "tools/call",
        "params": {
            "name": "interactive_config_wizard",
            "arguments": {
                "server_type": "ssh",
                "quick_mode": False
            }
        }
    }
    
    # 设置环境变量来模拟MCP环境
    env = os.environ.copy()
    env['NO_COLOR'] = '1'
    env['MCP_MODE'] = '1'
    
    print("🧪 测试MCP交互式配置向导...")
    
    try:
        # 启动MCP服务器进程
        proc = subprocess.Popen(
            [sys.executable, 'python/mcp_server.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # 发送测试请求
        request_json = json.dumps(test_request) + "\n"
        stdout, stderr = proc.communicate(input=request_json, timeout=10)
        
        print(f"📤 发送请求: {test_request['params']['name']}")
        print(f"📥 收到响应长度: {len(stdout)} 字符")
        
        if stdout:
            try:
                # 尝试解析响应为JSON
                response = json.loads(stdout.strip())
                print("✅ JSON解析成功！")
                
                if "result" in response and "content" in response["result"]:
                    content = response["result"]["content"][0]["text"]
                    print(f"📄 响应内容预览:\n{content[:200]}...")
                    
                    # 检查是否包含提示信息
                    if "配置向导启动提示" in content:
                        print("✅ 配置向导提示正常显示")
                        return True
                    else:
                        print("⚠️ 配置向导提示内容异常")
                        return False
                else:
                    print("❌ 响应格式异常")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                print(f"原始输出: {stdout}")
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

def test_mcp_create_server():
    """测试MCP创建服务器配置工具"""
    
    test_request = {
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
    
    env = os.environ.copy()
    env['NO_COLOR'] = '1'
    env['MCP_MODE'] = '1'
    
    print("\n🧪 测试MCP创建服务器配置...")
    
    try:
        proc = subprocess.Popen(
            [sys.executable, 'python/mcp_server.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        request_json = json.dumps(test_request) + "\n"
        stdout, stderr = proc.communicate(input=request_json, timeout=10)
        
        print(f"📤 发送请求: {test_request['params']['name']}")
        
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
                        print(f"⚠️ 意外的响应内容: {content}")
                        return False
                        
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                return False
        else:
            print("❌ 没有收到响应")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始MCP工具修复验证测试\n")
    
    # 切换到项目目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    test1_passed = test_mcp_interactive_config()
    test2_passed = test_mcp_create_server()
    
    print(f"\n📊 测试结果:")
    print(f"  interactive_config_wizard: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"  create_server_config: {'✅ 通过' if test2_passed else '❌ 失败'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 所有测试通过！MCP工具修复成功！")
        sys.exit(0)
    else:
        print("\n💔 部分测试失败，需要进一步调试")
        sys.exit(1) 