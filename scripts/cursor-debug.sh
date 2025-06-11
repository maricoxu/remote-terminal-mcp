#!/bin/bash

echo "🔍 Cursor环境诊断工具"
echo "=" * 50

echo "📊 基础环境信息："
echo "Node版本: $(node --version)"
echo "NPM版本: $(npm --version)"
echo "NPX版本: $(npx --version)"
echo "Python版本: $(python3 --version 2>/dev/null || echo 'Python3 not found')"
echo "工作目录: $(pwd)"
echo "用户: $(whoami)"
echo "Shell: $SHELL"

echo ""
echo "🌍 环境变量："
echo "PATH: $PATH"
echo "NODE_PATH: ${NODE_PATH:-'未设置'}"
echo "NPM_CONFIG_CACHE: ${NPM_CONFIG_CACHE:-'未设置'}"
echo "HOME: $HOME"

echo ""
echo "📦 NPM配置："
npm config list 2>/dev/null | head -10

echo ""
echo "🧪 MCP服务器长期运行测试："

# 创建临时测试脚本
cat > /tmp/mcp_longevity_test.py << 'EOF'
import json
import subprocess
import sys
import time
import signal

def signal_handler(sig, frame):
    print("\n💥 接收到中断信号，退出测试")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def test_mcp_longevity():
    print("🚀 启动长期运行MCP测试...")
    
    # 启动MCP服务器
    process = subprocess.Popen(
        ['npx', '-y', '@xuyehua/remote-terminal-mcp'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # 行缓冲
    )
    
    try:
        requests = [
            # 1. Initialize
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "cursor-test", "version": "1.0"}
                }
            },
            # 2. Tools list
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            },
            # 3. System info call
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "system_info",
                    "arguments": {}
                }
            }
        ]
        
        for i, request in enumerate(requests, 1):
            print(f"\n📤 发送请求 {i}: {request['method']}")
            
            # 发送请求
            request_str = json.dumps(request) + '\n'
            process.stdin.write(request_str)
            process.stdin.flush()
            
            # 读取响应 (设置超时)
            start_time = time.time()
            response_line = None
            
            while time.time() - start_time < 10:  # 10秒超时
                try:
                    if process.poll() is not None:
                        print(f"❌ 进程异常退出，代码: {process.returncode}")
                        break
                        
                    response_line = process.stdout.readline()
                    if response_line:
                        break
                        
                    time.sleep(0.1)
                except:
                    break
            
            if response_line:
                try:
                    response = json.loads(response_line.strip())
                    print(f"✅ 响应 {i}: 成功")
                    if 'result' in response:
                        if 'tools' in response.get('result', {}):
                            tools_count = len(response['result']['tools'])
                            print(f"   工具数量: {tools_count}")
                        elif 'content' in response.get('result', {}):
                            print(f"   内容长度: {len(str(response['result']['content']))}")
                except Exception as e:
                    print(f"❌ 响应 {i}: JSON解析失败 - {e}")
                    print(f"   原始响应: {response_line.strip()[:200]}")
            else:
                print(f"❌ 响应 {i}: 超时或无响应")
                
            # 检查stderr
            try:
                process.stderr.flush()
            except:
                pass
                
            time.sleep(1)  # 请求间隔
        
        print("\n⏱️  保持连接测试 (30秒)...")
        for i in range(6):
            if process.poll() is not None:
                print(f"❌ 进程在 {i*5} 秒后退出")
                break
            print(f"   {i*5}s: 进程仍在运行")
            time.sleep(5)
        
    finally:
        print("\n🛑 终止进程...")
        if process.poll() is None:
            process.terminate()
            time.sleep(2)
            if process.poll() is None:
                process.kill()
        
        # 获取stderr输出
        try:
            _, stderr = process.communicate(timeout=5)
            if stderr:
                print(f"\n📝 错误输出:")
                print(stderr[:1000])  # 限制输出长度
        except:
            pass

if __name__ == "__main__":
    test_mcp_longevity()
EOF

echo "执行长期运行测试..."
python3 /tmp/mcp_longevity_test.py

echo ""
echo "🧹 清理临时文件..."
rm -f /tmp/mcp_longevity_test.py

echo ""
echo "💡 建议："
echo "1. 如果测试失败，说明Cursor环境有特殊限制"
echo "2. 可能需要调整MCP服务器的环境适配"
echo "3. 检查Cursor的MCP配置是否正确" 