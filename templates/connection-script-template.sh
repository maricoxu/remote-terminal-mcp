#!/bin/bash

# Cursor-Bridge 服务器连接脚本模板
# 由NPM包自动生成

set -e

# =============================================================================
# 配置区域
# =============================================================================
SERVER_ID="{{SERVER_ID}}"
SERVER_NAME="{{SERVER_NAME}}"
SERVER_HOST="{{SERVER_HOST}}"
JUMP_HOST="{{JUMP_HOST}}"
CONTAINER_NAME="{{CONTAINER_NAME}}"
SESSION_NAME="{{SESSION_NAME}}"
BOS_BUCKET="bos:/klx-pytorch-work-bd-bj/xuyehua/template"

# =============================================================================
# 日志函数
# =============================================================================
log_info() {
    echo -e "\033[32m[INFO]\033[0m $1"
}

log_warn() {
    echo -e "\033[33m[WARN]\033[0m $1"
}

log_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

# =============================================================================
# 环境检查
# =============================================================================
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查SSH
    if ! command -v ssh &> /dev/null; then
        log_error "SSH未安装"
        exit 1
    fi
    
    # 检查tmux (可选)
    if ! command -v tmux &> /dev/null; then
        log_warn "tmux未安装，某些功能受限"
    fi
    
    log_info "依赖检查完成"
}

# =============================================================================
# 连接功能
# =============================================================================
connect_to_server() {
    log_info "连接到服务器: $SERVER_NAME ($SERVER_ID)"
    log_info "目标主机: $SERVER_HOST"
    
    if [ -n "$JUMP_HOST" ]; then
        log_info "通过跳板机: $JUMP_HOST"
        ssh -J "$JUMP_HOST" "$SERVER_HOST"
    else
        log_info "直接连接"
        ssh "$SERVER_HOST"
    fi
}

# =============================================================================
# Docker管理
# =============================================================================
setup_docker_environment() {
    log_info "设置Docker环境..."
    
    # 检查容器是否存在
    if docker ps -a --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
        log_info "容器 $CONTAINER_NAME 已存在"
        
        # 检查容器是否运行
        if docker ps --format "table {{.Names}}" | grep -q "^$CONTAINER_NAME$"; then
            log_info "容器正在运行"
        else
            log_info "启动容器..."
            docker start "$CONTAINER_NAME"
        fi
    else
        log_info "创建新容器..."
        create_docker_container
    fi
}

create_docker_container() {
    log_info "创建Docker容器: $CONTAINER_NAME"
    
    docker run -d -it \
        --name "$CONTAINER_NAME" \
        --gpus all \
        --net=host \
        --pid=host \
        --ipc=host \
        --privileged \
        -v /home:/home \
        -v /data:/data \
        -v /tmp:/tmp \
        iregistry.baidu-int.com/xmlir/xmlir_ubuntu_2004_x86_64:v0.32 \
        bash
    
    log_info "容器创建完成"
}

enter_container() {
    log_info "进入容器: $CONTAINER_NAME"
    docker exec -it "$CONTAINER_NAME" bash
}

# =============================================================================
# tmux会话管理
# =============================================================================
create_tmux_session() {
    log_info "创建tmux会话: $SESSION_NAME"
    
    # 检查会话是否已存在
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        log_info "会话已存在，连接到会话"
        tmux attach -t "$SESSION_NAME"
    else
        log_info "创建新会话"
        tmux new-session -d -s "$SESSION_NAME"
        tmux attach -t "$SESSION_NAME"
    fi
}

# =============================================================================
# BOS配置
# =============================================================================
setup_bos() {
    log_info "配置BOS..."
    
    # 设置BOS_BUCKET环境变量
    export BOS_BUCKET="$BOS_BUCKET"
    
    # 测试BOS连接
    if bcecmd bos cp --help &> /dev/null; then
        log_info "BOS配置成功"
    else
        log_warn "BOS配置可能有问题"
    fi
}

# =============================================================================
# 主函数
# =============================================================================
main() {
    echo "🌉 Cursor-Bridge 服务器连接脚本"
    echo "服务器: $SERVER_NAME ($SERVER_ID)"
    echo "主机: $SERVER_HOST"
    echo "容器: $CONTAINER_NAME"
    echo "会话: $SESSION_NAME"
    echo ""
    
    # 检查依赖
    check_dependencies
    
    # 根据模式执行
    case "${1:-connect}" in
        "connect")
            connect_to_server
            ;;
        "docker")
            setup_docker_environment
            enter_container
            ;;
        "tmux")
            create_tmux_session
            ;;
        "bos")
            setup_bos
            ;;
        "full")
            setup_docker_environment
            setup_bos
            create_tmux_session
            ;;
        *)
            echo "用法: $0 [connect|docker|tmux|bos|full]"
            echo ""
            echo "模式说明:"
            echo "  connect - 直接SSH连接到服务器"
            echo "  docker  - 设置并进入Docker容器"
            echo "  tmux    - 创建或连接tmux会话"
            echo "  bos     - 配置BOS环境"
            echo "  full    - 完整设置流程"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"