#!/bin/bash

# Remote Terminal MCP 快速体验脚本
# 让用户一键体验本地开发环境

echo "🚀 Remote Terminal MCP 快速体验"
echo "================================"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要Python3，请先安装"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
pip3 install -q pyyaml 2>/dev/null || {
    echo "⚠️  正在安装依赖: pyyaml"
    pip3 install pyyaml
}

# 启动MCP服务器（快速演示模式）
echo ""
echo "🎯 启动MCP服务器..."
echo ""

# 设置静默模式，避免启动摘要重复
export MCP_QUIET=1

cd "$(dirname "$0")/.."
python3 python/mcp_server.py &
MCP_PID=$!

echo "✅ MCP服务器已启动 (PID: $MCP_PID)"
echo ""
echo "🔧 可用的MCP工具:"
echo "   • system_info     - 查看系统信息"
echo "   • run_command     - 执行本地命令"
echo "   • list_tmux_sessions - 列出tmux会话"
echo "   • create_tmux_session - 创建新会话"
echo "   • list_directory  - 浏览目录"
echo ""
echo "💡 使用提示:"
echo "   • 本地开发环境已就绪"
echo "   • tmux会话: dev-session"
echo "   • 配置远程连接: ~/.remote-terminal/config.yaml"
echo ""
echo "⏹️  按 Ctrl+C 停止服务器"

# 等待用户中断
trap "echo ''; echo '🛑 正在停止MCP服务器...'; kill $MCP_PID 2>/dev/null; echo '✅ 已停止'; exit 0" INT

# 保持脚本运行
wait $MCP_PID 