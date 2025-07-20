#!/bin/bash

# Remote Terminal MCP 本地开发脚本
# 用于快速设置和测试本地MCP环境

set -e

echo "🚀 Remote Terminal MCP 本地开发环境"
echo "=================================="

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
MCP_CONFIG_FILE="$HOME/.cursor/mcp.json"

# 函数：显示帮助信息
show_help() {
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  setup     - 设置本地MCP配置"
    echo "  test      - 运行MCP服务器测试"
    echo "  start     - 启动MCP服务器"
    echo "  config    - 显示当前配置"
    echo "  clean     - 清理测试文件"
    echo "  help      - 显示此帮助信息"
    echo ""
}

# 函数：设置本地MCP配置
setup_local_mcp() {
    echo "📁 项目路径: $PROJECT_ROOT"
    
    # 检查Python依赖
    echo "🔍 检查Python依赖..."
    if ! python3 -c "import sys; print(f'Python {sys.version}')"; then
        echo "❌ Python3 未安装"
        exit 1
    fi
    
    # 安装Python依赖
    echo "📦 安装Python依赖..."
    python3 -m pip install -r requirements.txt --user --quiet
    
    # 创建本地MCP配置
    echo "⚙️  创建Cursor MCP配置..."
    
    mkdir -p ~/.cursor
    
    # 生成MCP配置
    cat > "$MCP_CONFIG_FILE.local" << EOF
{
  "mcpServers": {
    "remote-terminal-mcp-local": {
      "command": "node",
      "args": ["$PROJECT_ROOT/index.js"],
      "env": {
        "MCP_DEBUG": "1",
        "PYTHONPATH": "$PROJECT_ROOT",
        "MCP_LOCAL_MODE": "true"
      }
    }
  }
}
EOF

    echo "✅ 本地MCP配置已创建: $MCP_CONFIG_FILE.local"
    echo ""
    echo "📋 要在Cursor中使用本地版本，请将以下内容添加到 ~/.cursor/mcp.json:"
    echo ""
    cat "$MCP_CONFIG_FILE.local"
    echo ""
}

# 函数：测试MCP服务器
test_mcp_server() {
    echo "🧪 运行MCP服务器测试..."
    node test_local_mcp.js
}

# 函数：启动MCP服务器
start_mcp_server() {
    echo "🚀 启动MCP服务器 (按Ctrl+C停止)..."
    echo "项目路径: $PROJECT_ROOT"
    echo ""
    
    MCP_DEBUG=1 MCP_LOCAL_MODE=true PYTHONPATH="$PROJECT_ROOT" node index.js
}

# 函数：显示当前配置
show_config() {
    echo "📋 当前配置信息:"
    echo "项目路径: $PROJECT_ROOT"
    echo "MCP配置文件: $MCP_CONFIG_FILE.local"
    echo ""
    
    if [ -f "$MCP_CONFIG_FILE.local" ]; then
        echo "本地MCP配置内容:"
        cat "$MCP_CONFIG_FILE.local"
    else
        echo "❌ 本地MCP配置文件不存在，请先运行 'setup'"
    fi
}

# 函数：清理测试文件
clean_test_files() {
    echo "🧹 清理测试文件..."
    rm -f test_local_mcp.js
    rm -f mcp-local.json
    rm -f "$MCP_CONFIG_FILE.local"
    echo "✅ 清理完成"
}

# 主逻辑
case "${1:-help}" in
    "setup")
        setup_local_mcp
        ;;
    "test")
        test_mcp_server
        ;;
    "start")
        start_mcp_server
        ;;
    "config")
        show_config
        ;;
    "clean")
        clean_test_files
        ;;
    "help"|*)
        show_help
        ;;
esac 