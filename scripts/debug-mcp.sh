#!/bin/bash

echo "🔍 Remote Terminal MCP 调试工具"
echo "================================"

echo "📦 检查当前npm包版本..."
npm list -g @xuyehua/remote-terminal-mcp 2>/dev/null || echo "未全局安装"
npx @xuyehua/remote-terminal-mcp --version 2>/dev/null || echo "无法获取版本"

echo ""
echo "🧪 直接测试MCP服务器..."
echo "发送initialize请求..."

# 创建临时测试脚本
cat > /tmp/test_mcp.py << 'EOF'
import json
import subprocess
import sys
import os

# 设置调试模式
os.environ['MCP_DEBUG'] = '1'

def test_mcp_server():
    print("🚀 启动MCP服务器进程...")
    
    # 启动MCP服务器
    process = subprocess.Popen(
        ['npx', '-y', '@xuyehua/remote-terminal-mcp'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )
    
    try:
        # 发送initialize请求
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
        
        print("📤 发送initialize请求...")
        print(f"Request: {json.dumps(initialize_request, indent=2)}")
        
        process.stdin.write(json.dumps(initialize_request) + '\n')
        process.stdin.flush()
        
        # 读取响应
        print("📥 等待响应...")
        response_line = process.stdout.readline()
        print(f"Response: {response_line.strip()}")
        
        if response_line.strip():
            try:
                response = json.loads(response_line.strip())
                print("✅ Initialize成功!")
                print(f"服务器信息: {json.dumps(response, indent=2)}")
            except:
                print("❌ 响应不是有效JSON")
        
        # 发送tools/list请求
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        print("\n📤 发送tools/list请求...")
        process.stdin.write(json.dumps(tools_request) + '\n')
        process.stdin.flush()
        
        # 读取工具列表响应
        tools_response_line = process.stdout.readline()
        print(f"Tools Response: {tools_response_line.strip()}")
        
        if tools_response_line.strip():
            try:
                tools_response = json.loads(tools_response_line.strip())
                tools = tools_response.get('result', {}).get('tools', [])
                print(f"✅ 找到 {len(tools)} 个工具!")
                for tool in tools:
                    print(f"  - {tool.get('name')}: {tool.get('description')}")
            except Exception as e:
                print(f"❌ 工具列表响应解析失败: {e}")
        
        # 等待一下查看stderr输出
        import time
        time.sleep(2)
        
    finally:
        print("\n🛑 终止MCP服务器...")
        process.terminate()
        
        # 输出stderr (调试日志)
        stderr_output = process.stderr.read()
        if stderr_output:
            print("\n📝 调试日志:")
            print("=" * 50)
            print(stderr_output)
            print("=" * 50)

if __name__ == "__main__":
    test_mcp_server()
EOF

echo "执行MCP测试..."
python3 /tmp/test_mcp.py

echo ""
echo "🔧 如果问题依然存在，请:"
echo "1. 重启Cursor"
echo "2. 检查Cursor MCP日志"
echo "3. 确认 ~/.cursor/mcp.json 配置正确"

# 清理临时文件
rm -f /tmp/test_mcp.py 