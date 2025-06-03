#!/bin/bash
# CPU-221 服务器连接脚本 - 完整功能版本
# 包含智能会话管理 + 完整环境配置 + BOS配置下载

# 配置信息
SESSION_NAME="cpu221_dev"
CONNECTION_TOOL="relay-cli"

# 目标服务器配置（直连模式）
SERVER_HOST="bjhw-sys-rpm0221.bjhw"
DOCKER_CONTAINER="xyh_pytorch"
DOCKER_IMAGE="iregistry.baidu-int.com/xmlir/xmlir_ubuntu_2004_x86_64:v0.32"

# 环境配置选项
AUTO_SETUP_ENVIRONMENT=true
QUICK_CONNECT_MODE=true

# BOS配置信息（仅首次环境配置时使用）
BOS_ACCESS_KEY="ALTAKhAZPC4OOKQ2zm"
BOS_SECRET_KEY="your_secret_key"  # 请填入实际的secret key
BOS_BUCKET="bos://klx-pytorch-work-bd-bj/xuyehua/template"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 智能检查tmux输出函数
check_tmux_output() {
    local session_name=$1
    local expected_pattern=$2
    local timeout=${3:-10}
    local check_interval=1
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        local output=$(tmux capture-pane -t $session_name -p | grep -v '^$' | tail -10)
        if [[ "$output" =~ $expected_pattern ]]; then
            return 0
        fi
        sleep $check_interval
        elapsed=$((elapsed + check_interval))
    done
    return 1
}

# 智能容器检查和处理函数
smart_container_setup() {
    local session_name=$1
    local container_name=$2
    local image_name=$3
    
    echo -e "${BLUE}🔍 智能检查Docker环境...${NC}"
    
    # 步骤1：精确检查容器是否存在
    echo -e "${BLUE}🔍 步骤1: 精确检查容器是否存在: $container_name${NC}"
    tmux send-keys -t $session_name "echo '=== CONTAINER_EXIST_CHECK_START ==='" Enter
    tmux send-keys -t $session_name "docker inspect $container_name >/dev/null 2>&1 && echo 'CONTAINER_EXISTS_YES' || echo 'CONTAINER_EXISTS_NO'" Enter
    sleep 3
    
    # 获取检查结果
    echo -e "${YELLOW}正在捕获检查结果...${NC}"
    tmux send-keys -t $session_name "echo '=== CAPTURE_POINT ==='" Enter
    sleep 1
    
    local exist_output=$(tmux capture-pane -t $session_name -p | sed -n '/=== CONTAINER_EXIST_CHECK_START ===/,/=== CAPTURE_POINT ===/p' | grep -E "(CONTAINER_EXISTS_YES|CONTAINER_EXISTS_NO)" | tail -1)
    
    echo -e "${YELLOW}调试信息 - 容器存在性检查:${NC}"
    echo "检查结果: [$exist_output]"
    
    if [[ "$exist_output" == *"CONTAINER_EXISTS_YES"* ]]; then
        echo -e "${GREEN}✅ 容器已存在，进入快速连接模式...${NC}"
        handle_existing_container $session_name $container_name
        return $?
        
    elif [[ "$exist_output" == *"CONTAINER_EXISTS_NO"* ]]; then
        echo -e "${BLUE}🚀 容器不存在，进入创建模式...${NC}"
        handle_new_container $session_name $container_name $image_name
        return $?
        
    else
        echo -e "${RED}❌ 容器存在性检查结果异常${NC}"
        echo -e "${YELLOW}调试信息 - 原始输出:${NC}"
        tmux capture-pane -t $session_name -p | tail -10
        return 1
    fi
}

# 处理已存在容器的逻辑
handle_existing_container() {
    local session_name=$1
    local container_name=$2
    
    echo -e "${BLUE}🔍 步骤2: 检查容器运行状态...${NC}"
    tmux send-keys -t $session_name "echo '=== CONTAINER_STATUS_CHECK_START ==='" Enter
    tmux send-keys -t $session_name "docker inspect --format='{{.State.Running}}' $container_name" Enter
    sleep 2
    
    local status_output=$(tmux capture-pane -t $session_name -p | grep -A 3 "=== CONTAINER_STATUS_CHECK_START ===" | tail -2)
    echo -e "${YELLOW}调试信息 - 容器运行状态:${NC}"
    echo "$status_output"
    
    if echo "$status_output" | grep -q "true"; then
        echo -e "${GREEN}✅ 容器正在运行${NC}"
    else
        echo -e "${YELLOW}⚠️  容器已停止，正在启动...${NC}"
        tmux send-keys -t $session_name "echo '=== CONTAINER_START_BEGIN ==='" Enter
        tmux send-keys -t $session_name "docker start $container_name" Enter
        sleep 5
        
        local start_result=$(tmux capture-pane -t $session_name -p | grep -A 3 "=== CONTAINER_START_BEGIN ===" | tail -2)
        if echo "$start_result" | grep -q "$container_name"; then
            echo -e "${GREEN}✅ 容器启动成功${NC}"
        else
            echo -e "${RED}❌ 容器启动失败${NC}"
            echo -e "${YELLOW}错误信息: $start_result${NC}"
            return 1
        fi
    fi
    
    # 进入容器
    echo -e "${GREEN}🚪 步骤3: 进入现有容器...${NC}"
    tmux send-keys -t $session_name "docker exec -it $container_name zsh" Enter
    sleep 2
    
    # 检查是否成功进入zsh
    if ! check_tmux_output $session_name ".*@.*:.*#" 5; then
        echo -e "${YELLOW}⚠️  尝试启动zsh...${NC}"
        tmux send-keys -t $session_name "zsh" Enter
        sleep 2
    fi
    
    echo -e "${GREEN}✅ 快速连接完成！${NC}"
    return 0
}

# 处理新容器创建的逻辑
handle_new_container() {
    local session_name=$1
    local container_name=$2
    local image_name=$3
    
    echo -e "${BLUE}步骤1: 创建Docker容器 $container_name${NC}"
    tmux send-keys -t $session_name "echo '=== CONTAINER_CREATE_START ==='" Enter
    tmux send-keys -t $session_name "docker run --privileged --name=$container_name --ulimit core=-1 --security-opt seccomp=unconfined -dti --net=host --uts=host --ipc=host --security-opt=seccomp=unconfined -v /home:/home -v /data1:/data1 -v /data2:/data2 -v /data3:/data3 -v /data4:/data4 --shm-size=256g --restart=always $image_name" Enter
    sleep 10
    
    # 验证容器创建
    echo -e "${BLUE}步骤2: 验证容器创建结果${NC}"
    tmux send-keys -t $session_name "echo '=== VERIFY_CREATE_START ==='" Enter
    tmux send-keys -t $session_name "docker inspect $container_name >/dev/null 2>&1 && echo 'CREATE_SUCCESS' || echo 'CREATE_FAILED'" Enter
    sleep 3
    
    local verify_output=$(tmux capture-pane -t $session_name -p | grep -A 3 "=== VERIFY_CREATE_START ===" | tail -2)
    
    if echo "$verify_output" | grep -q "CREATE_SUCCESS"; then
        echo -e "${GREEN}✅ 容器创建成功${NC}"
    else
        echo -e "${RED}❌ 容器创建失败${NC}"
        echo -e "${YELLOW}调试信息: $verify_output${NC}"
        return 1
    fi
    
    # 进入新创建的容器
    echo -e "${GREEN}🚪 步骤3: 进入新创建的容器...${NC}"
    tmux send-keys -t $session_name "docker exec -it $container_name bash" Enter
    sleep 3
    
    if ! check_tmux_output $session_name "root@.*#" 5; then
        echo -e "${RED}❌ 进入容器失败${NC}"
        return 1
    fi
    
    # 如果启用自动环境配置，执行完整配置
    if [ "$AUTO_SETUP_ENVIRONMENT" = "true" ]; then
        setup_full_environment $session_name
    else
        echo -e "${YELLOW}💡 容器已创建，如需配置环境请手动执行相关命令${NC}"
    fi
    
    return 0
}

# 完整环境配置函数
setup_full_environment() {
    local session_name=$1
    
    echo -e "${BLUE}🛠️  开始完整环境配置...${NC}"
    
    # 检查BOS工具
    echo -e "${BLUE}步骤1: 检查BOS工具${NC}"
    tmux send-keys -t $session_name "which bcecmd" Enter
    sleep 2
    
    if check_tmux_output $session_name "/.*bcecmd" 5; then
        echo -e "${GREEN}✅ BOS工具可用${NC}"
        
        # 配置BOS
        echo -e "${BLUE}步骤2: 配置BOS工具${NC}"
        echo "启动bcecmd配置..."
        tmux send-keys -t $session_name "bcecmd -c" Enter
        sleep 3

        echo "输入Access Key..."
        tmux send-keys -t $session_name "$BOS_ACCESS_KEY" Enter
        sleep 0.1

        echo "输入Secret Key..."
        tmux send-keys -t $session_name "$BOS_SECRET_KEY" Enter
        sleep 0.1

        echo "使用默认配置（连续回车）..."
        for i in {1..11}; do
            echo "  发送第${i}个回车..."
            tmux send-keys -t $session_name "" Enter
            sleep 0.1
        done
        
        sleep 5

        # 测试BOS连接并下载配置文件
        echo -e "${BLUE}步骤3: 测试BOS连接并下载配置文件${NC}"
        echo -e "${YELLOW}调试信息 - BOS_BUCKET: $BOS_BUCKET${NC}"
        
        echo "测试下载.p10k.zsh配置..."
        tmux send-keys -t $session_name "echo '=== BOS_DOWNLOAD_START ==='" Enter
        tmux send-keys -t $session_name "bcecmd bos cp -y $BOS_BUCKET/.p10k.zsh /root" Enter
        sleep 5
        
        # 检查下载是否成功
        tmux send-keys -t $session_name "echo '=== BOS_DOWNLOAD_CHECK ==='" Enter
        tmux send-keys -t $session_name "if [ -f /root/.p10k.zsh ]; then echo 'BOS_DOWNLOAD_SUCCESS'; else echo 'BOS_DOWNLOAD_FAILED'; fi" Enter
        sleep 2
        
        local download_output=$(tmux capture-pane -t $session_name -p | tail -10)
        
        if echo "$download_output" | grep -q "BOS_DOWNLOAD_SUCCESS"; then
            echo -e "${GREEN}✅ BOS配置和连接成功！${NC}"
            
            # 继续下载其他配置文件
            echo "下载.zshrc配置..."
            tmux send-keys -t $session_name "bcecmd bos cp -y $BOS_BUCKET/.zshrc /root" Enter
            sleep 5

            echo "下载.zsh_history配置..."
            tmux send-keys -t $session_name "bcecmd bos cp -y $BOS_BUCKET/.zsh_history /root" Enter
            sleep 5

            # 验证所有配置文件
            echo -e "${BLUE}步骤4: 验证配置文件${NC}"
            tmux send-keys -t $session_name "ls -la /root/.zshrc /root/.p10k.zsh /root/.zsh_history" Enter
            sleep 2

            if check_tmux_output $session_name "\.zshrc.*\.p10k\.zsh.*\.zsh_history" 5; then
                echo -e "${GREEN}✅ 所有配置文件下载成功${NC}"
            else
                echo -e "${YELLOW}⚠️  部分配置文件可能下载失败，但核心配置已成功${NC}"
            fi
            
            echo -e "${GREEN}✅ 配置文件下载完成，p10k主题将在zsh启动时自动加载${NC}"
            
        else
            echo -e "${RED}❌ BOS连接或下载失败！${NC}"
            echo -e "${YELLOW}🔍 BOS操作输出：${NC}"
            echo "$download_output"
            echo -e "${RED}🛑 BOS下载失败，切换到本地配置${NC}"
            setup_local_config $session_name
        fi
    else
        echo -e "${YELLOW}⚠️  BOS工具不可用，使用本地备用配置${NC}"
        setup_local_config $session_name
    fi
    
    # 创建工作目录
    echo -e "${BLUE}步骤5: 创建工作目录${NC}"
    tmux send-keys -t $session_name "mkdir -p /home/xuyehua" Enter
    sleep 1
    
    # 生成SSH密钥
    echo -e "${BLUE}步骤6: 生成SSH密钥${NC}"
    echo "生成SSH密钥（使用默认设置）..."
    tmux send-keys -t $session_name "ssh-keygen -t rsa -f ~/.ssh/id_rsa -N ''" Enter
    sleep 3
    
    # 启动zsh环境
    echo -e "${BLUE}步骤7: 启动zsh环境${NC}"
    tmux send-keys -t $session_name "echo '=== 启动zsh ==='" Enter
    tmux send-keys -t $session_name "zsh" Enter
    sleep 3
    
    # 显示SSH公钥
    echo -e "${BLUE}步骤8: 显示SSH公钥${NC}"
    tmux send-keys -t $session_name "echo \"=== SSH_KEY_DISPLAY_START ===\"" Enter
    tmux send-keys -t $session_name "if [ -f /root/.ssh/id_rsa.pub ]; then cat /root/.ssh/id_rsa.pub; else echo \"SSH公钥文件不存在\"; fi" Enter
    sleep 2
    
    # 捕获并显示公钥内容
    local ssh_key_output=$(tmux capture-pane -t $session_name -p | grep -A 3 "=== SSH_KEY_DISPLAY_START ===" | tail -2 | grep -v "^$" | head -1)
    if [ -n "$ssh_key_output" ] && ! echo "$ssh_key_output" | grep -q "不存在"; then
        echo -e "${GREEN}✅ SSH公钥已生成，内容如下：${NC}"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}$ssh_key_output${NC}"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}💡 请复制上述公钥内容到目标服务器的authorized_keys文件${NC}"
    else
        echo -e "${YELLOW}⚠️  SSH公钥获取失败，请手动执行: cat /root/.ssh/id_rsa.pub${NC}"
    fi
    
    echo -e "${GREEN}✅ 完整环境配置完成！${NC}"
}

# 本地配置备用方案
setup_local_config() {
    local session_name=$1
    echo -e "${BLUE}🔧 设置本地备用配置...${NC}"
    tmux send-keys -t $session_name "echo 'export TERM=xterm-256color' >> ~/.bashrc" Enter
    sleep 1
    tmux send-keys -t $session_name "source ~/.bashrc" Enter
    sleep 1
    echo -e "${GREEN}✅ 本地配置完成${NC}"
}

# 智能会话管理函数
smart_session_management() {
    echo -e "${BLUE}🔍 检查tmux会话状态...${NC}"
    
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo -e "${GREEN}✅ 发现已存在的会话: $SESSION_NAME${NC}"
        echo -e "${CYAN}🚀 直接连接到现有会话...${NC}"
        tmux attach -t "$SESSION_NAME"
        return 0
    else
        echo -e "${YELLOW}📋 会话不存在，创建新环境...${NC}"
        return 1
    fi
}

# 主执行流程
main() {
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}CPU-221 智能连接系统 (完整版)${NC}"
    echo -e "${CYAN}================================${NC}"
    echo "目标服务器: $SERVER_HOST"
    echo "Docker容器: $DOCKER_CONTAINER"
    echo "快速连接模式: $QUICK_CONNECT_MODE"
    echo ""
    
    # 尝试智能会话管理
    if ! smart_session_management; then
        # 会话不存在，创建新环境
        echo -e "${BLUE}🚀 创建新的tmux session: $SESSION_NAME${NC}"
        tmux new-session -d -s $SESSION_NAME

        echo -e "${BLUE}📡 步骤1: 启动连接工具 ($CONNECTION_TOOL)${NC}"
        tmux send-keys -t $SESSION_NAME "$CONNECTION_TOOL" Enter

        echo -e "${YELLOW}✋ 请完成指纹认证...${NC}"
        sleep 2

        echo -e "${BLUE}🎯 步骤2: 直接连接到目标服务器 ($SERVER_HOST)${NC}"
        tmux send-keys -t $SESSION_NAME "ssh $SERVER_HOST" Enter

        echo -e "${YELLOW}等待服务器连接建立...${NC}"
        sleep 3

        # 智能Docker环境设置
        echo -e "${BLUE}🐳 步骤3: 智能Docker环境设置${NC}"
        smart_container_setup "$SESSION_NAME" "$DOCKER_CONTAINER" "$DOCKER_IMAGE"

        echo -e "${GREEN}✅ 连接流程完成${NC}"
        echo ""
        echo -e "${CYAN}💡 功能说明：${NC}"
        echo -e "${CYAN}  🎯 连接流程: $CONNECTION_TOOL → $SERVER_HOST → Docker容器${NC}"
        echo -e "${CYAN}  🚀 智能模式: 自动检测容器状态，快速进入或完整配置${NC}"
        echo -e "${CYAN}  ⚡ 快速连接: 现有容器直接进入，无需重复配置${NC}"
        echo -e "${CYAN}  🛠️  完整配置: 新容器自动配置BOS、SSH密钥、zsh环境${NC}"
    fi
    
    # 无论如何都连接到session
    echo -e "${CYAN}🚀 连接到会话: $SESSION_NAME${NC}"
    tmux attach -t $SESSION_NAME
}

# 启动主程序
main 