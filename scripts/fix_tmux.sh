#!/bin/bash
# 修复tmux连接问题的脚本

echo "🔧 修复tmux连接问题..."

# 检查tmux是否安装
if ! command -v tmux &> /dev/null; then
    echo "❌ tmux未安装，请先安装tmux"
    exit 1
fi

# 检查是否有tmux会话在运行
if tmux list-sessions &> /dev/null; then
    echo "✅ tmux会话已存在，无需修复"
    tmux list-sessions
    exit 0
fi

# 清理可能存在的损坏的socket文件
echo "🧹 清理可能存在的损坏的socket文件..."
rm -f /private/tmp/tmux-*/default

# 启动新的tmux会话
echo "🚀 启动新的tmux会话..."
tmux new-session -d -s default

# 验证tmux是否正常工作
if tmux list-sessions &> /dev/null; then
    echo "✅ tmux修复成功！"
    tmux list-sessions
else
    echo "❌ tmux修复失败"
    exit 1
fi 