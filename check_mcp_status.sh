#!/bin/bash

# MCP状态检查脚本
# 快速查看本地MCP环境的状态

echo "🔍 Remote Terminal MCP 状态检查"
echo "==============================="

# 检查项目文件
echo "📁 项目文件检查:"
echo "  index.js: $([ -f index.js ] && echo '✅' || echo '❌')"
echo "  python/mcp_server.py: $([ -f python/mcp_server.py ] && echo '✅' || echo '❌')"
echo "  enhanced_config_manager.py: $([ -f enhanced_config_manager.py ] && echo '✅' || echo '❌')"
echo "  package.json: $([ -f package.json ] && echo '✅' || echo '❌')"

# 检查Python环境
echo ""
echo "🐍 Python环境检查:"
if command -v python3 >/dev/null 2>&1; then
    echo "  Python3: ✅ $(python3 --version)"
else
    echo "  Python3: ❌ 未找到"
fi

# 检查Node.js环境
echo ""
echo "🟢 Node.js环境检查:"
if command -v node >/dev/null 2>&1; then
    echo "  Node.js: ✅ $(node --version)"
else
    echo "  Node.js: ❌ 未找到"
fi

# 检查MCP配置
echo ""
echo "⚙️  MCP配置检查:"
if [ -f ~/.cursor/mcp.json ]; then
    echo "  Cursor MCP配置: ✅ 存在"
    node update_mcp_config.js status 2>/dev/null | grep -E "本地版本|NPM版本" | sed 's/^/  /'
else
    echo "  Cursor MCP配置: ❌ 不存在"
fi

# 检查脚本权限
echo ""
echo "🔐 脚本权限检查:"
echo "  local-dev.sh: $([ -x local-dev.sh ] && echo '✅ 可执行' || echo '❌ 不可执行')"
echo "  test_local_mcp.js: $([ -x test_local_mcp.js ] && echo '✅ 可执行' || echo '❌ 不可执行')"

# 检查Python依赖
echo ""
echo "📦 Python依赖检查:"
if python3 -c "import yaml" 2>/dev/null; then
    echo "  PyYAML: ✅ 已安装"
else
    echo "  PyYAML: ❌ 未安装"
fi

# 检查配置文件
echo ""
echo "📋 配置文件检查:"
if [ -f ~/.remote-terminal/config.yaml ]; then
    echo "  远程终端配置: ✅ 存在"
    echo "  服务器数量: $(grep -c "^  [a-zA-Z]" ~/.remote-terminal/config.yaml 2>/dev/null || echo "0")"
else
    echo "  远程终端配置: ❌ 不存在"
fi

# 建议操作
echo ""
echo "💡 建议操作:"

if [ ! -f ~/.cursor/mcp.json ]; then
    echo "  - 运行 'node update_mcp_config.js add-local' 配置本地MCP"
fi

if [ ! -x local-dev.sh ]; then
    echo "  - 运行 'chmod +x local-dev.sh' 添加执行权限"
fi

if ! python3 -c "import yaml" 2>/dev/null; then
    echo "  - 运行 'python3 -m pip install -r requirements.txt --user' 安装依赖"
fi

echo ""
echo "🚀 快速开始:"
echo "  ./local-dev.sh setup   # 设置环境"
echo "  ./local-dev.sh test    # 测试功能"
echo "  ./local-dev.sh start   # 启动服务器"

echo ""
echo "完成状态检查 ✅" 