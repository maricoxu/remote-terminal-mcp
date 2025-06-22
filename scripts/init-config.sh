#!/bin/bash

# Remote Terminal MCP 简单安装脚本
# 创建用户配置目录和默认配置文件

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# 配置路径
USER_CONFIG_DIR="$HOME/.remote-terminal"
CONFIG_FILE="$USER_CONFIG_DIR/config.yaml"
TEMPLATE_FILE="config/servers.template.yaml"

print_header() {
    echo -e "${BOLD}${BLUE}🚀 Remote Terminal MCP 安装${NC}"
    echo -e "${BLUE}========================${NC}"
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_step() {
    echo -e "${YELLOW}[STEP]${NC} $1"
}

main() {
    print_header
    
    # 第1步：创建用户配置目录
    print_step "1/3 创建配置目录"
    if [ ! -d "$USER_CONFIG_DIR" ]; then
        mkdir -p "$USER_CONFIG_DIR"
        print_info "已创建配置目录: $USER_CONFIG_DIR"
    else
        print_info "配置目录已存在: $USER_CONFIG_DIR"
    fi
    
    # 第2步：复制默认配置
    print_step "2/3 安装默认配置"
    if [ ! -f "$CONFIG_FILE" ]; then
        cp "$TEMPLATE_FILE" "$CONFIG_FILE"
        print_info "已安装默认配置: $CONFIG_FILE"
    else
        print_info "配置文件已存在，跳过覆盖"
    fi
    
    # 第3步：创建默认tmux会话（如果不存在）
    print_step "3/3 检查tmux会话"
    if command -v tmux >/dev/null 2>&1; then
        if ! tmux has-session -t dev-session 2>/dev/null; then
            tmux new-session -d -s dev-session -c "$HOME/Code" 2>/dev/null || \
            tmux new-session -d -s dev-session -c "$HOME" 2>/dev/null || \
            print_info "请手动创建tmux会话: tmux new-session -d -s dev-session"
            
            if tmux has-session -t dev-session 2>/dev/null; then
                print_info "已创建默认tmux会话: dev-session"
            fi
        else
            print_info "tmux会话已存在: dev-session"
        fi
    else
        print_info "未检测到tmux，请安装: brew install tmux (macOS) 或 apt install tmux (Linux)"
    fi
    
    # 完成信息
    echo ""
    echo -e "${GREEN}✅ 安装完成！${NC}"
    echo ""
    echo -e "${BOLD}📝 快速开始:${NC}"
    echo -e "${CYAN}1. 配置文件位置: $CONFIG_FILE${NC}"
    echo -e "${CYAN}2. 编辑配置 (可选): nano $CONFIG_FILE${NC}"
    echo -e "${CYAN}3. 启动MCP服务器: python3 python/mcp_server.py${NC}"
    echo -e "${CYAN}4. 在Cursor中测试: \"列出所有tmux会话\"${NC}"
    echo ""
    echo -e "${BOLD}🎯 默认配置说明:${NC}"
    echo -e "${CYAN}• 连接到本地tmux会话 'dev-session'${NC}"
    echo -e "${CYAN}• 工作目录: ~/Code (如果存在) 或 ~${NC}"
    echo -e "${CYAN}• 开箱即用，无需额外配置${NC}"
    echo ""
    
    # 显示配置文件路径，方便用户编辑
    if command -v code >/dev/null 2>&1; then
        echo -e "${YELLOW}💡 使用VS Code编辑配置: code $CONFIG_FILE${NC}"
    elif command -v nano >/dev/null 2>&1; then
        echo -e "${YELLOW}💡 使用nano编辑配置: nano $CONFIG_FILE${NC}"
    fi
}

# 运行主函数
main "$@" 