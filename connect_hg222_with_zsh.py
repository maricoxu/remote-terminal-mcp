#!/usr/bin/env python3
"""
连接hg222服务器并自动应用zsh配置的脚本
"""

import subprocess
import time
import sys
from pathlib import Path

def log_message(message, level="INFO"):
    """打印日志消息"""
    icons = {
        "INFO": "ℹ️",
        "SUCCESS": "✅", 
        "WARNING": "⚠️",
        "ERROR": "❌"
    }
    icon = icons.get(level, "📝")
    print(f"{icon} {message}")

def connect_hg222_with_zsh():
    """连接hg222并应用zsh配置"""
    
    session_name = "hg222_session"
    
    log_message("开始连接hg222服务器...")
    
    # 1. 检查是否已有会话
    result = subprocess.run(['tmux', 'has-session', '-t', session_name], 
                          capture_output=True)
    if result.returncode == 0:
        log_message("检测到现有会话，将重新创建...")
        subprocess.run(['tmux', 'kill-session', '-t', session_name], 
                      capture_output=True)
    
    # 2. 创建新会话
    log_message("创建tmux会话...")
    subprocess.run(['tmux', 'new-session', '-d', '-s', session_name])
    
    # 3. 启动relay-cli
    log_message("启动relay-cli...")
    subprocess.run(['tmux', 'send-keys', '-t', session_name, 'relay-cli', 'Enter'])
    
    # 4. 等待relay启动
    log_message("等待relay连接...")
    time.sleep(10)
    
    # 5. 连接到szzj跳板机
    log_message("连接到szzj跳板机...")
    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                   'ssh yh@szzj-isa-ai-peking-poc06.szzj', 'Enter'])
    time.sleep(3)
    
    # 6. 输入密码
    log_message("输入跳板机密码...")
    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                   'kunlunxin@yh123', 'Enter'])
    time.sleep(5)
    
    # 7. 连接到目标服务器
    log_message("连接到目标服务器...")
    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                   'ssh root@10.129.130.222', 'Enter'])
    time.sleep(5)
    
    # 8. 进入Docker容器
    log_message("进入Docker容器...")
    subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                   'docker exec -it xyh_pytorch bash', 'Enter'])
    time.sleep(3)
    
    # 9. 复制zsh配置文件
    log_message("复制zsh配置文件...")
    copy_zsh_config(session_name)
    
    # 10. 启动zsh
    log_message("启动zsh环境...")
    subprocess.run(['tmux', 'send-keys', '-t', session_name, 'zsh', 'Enter'])
    time.sleep(2)
    
    log_message("连接完成！", "SUCCESS")
    log_message(f"使用以下命令进入会话: tmux attach -t {session_name}")

def copy_zsh_config(session_name: str):
    """复制zsh配置文件到容器"""
    
    # 配置文件路径
    config_dir = Path(__file__).parent / "templates" / "configs" / "zsh"
    
    if not config_dir.exists():
        log_message(f"配置目录不存在: {config_dir}", "ERROR")
        return False
    
    log_message(f"从配置目录复制: {config_dir}")
    
    # 复制每个配置文件
    copied_files = 0
    for config_file in config_dir.glob(".*"):
        if config_file.is_file():
            log_message(f"复制配置文件: {config_file.name}")
            
            try:
                # 读取配置文件内容，处理编码问题
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # 如果是二进制文件（如.zsh_history），跳过
                    log_message(f"跳过二进制文件: {config_file.name}", "WARNING")
                    continue
                
                # 在容器内创建配置文件
                create_cmd = f"cat > ~/{config_file.name} << 'EOF_CONFIG_FILE'\\n{content}\\nEOF_CONFIG_FILE"
                
                # 发送命令到容器
                subprocess.run(['tmux', 'send-keys', '-t', session_name, create_cmd, 'Enter'],
                             capture_output=True)
                time.sleep(1)
                
                log_message(f"已创建: {config_file.name}", "SUCCESS")
                copied_files += 1
                
            except Exception as e:
                log_message(f"处理配置文件失败: {config_file.name} - {str(e)}", "WARNING")
    
    if copied_files > 0:
        log_message(f"成功复制 {copied_files} 个配置文件", "SUCCESS")
        return True
    else:
        log_message("未找到可复制的配置文件", "WARNING")
        return False

if __name__ == "__main__":
    try:
        connect_hg222_with_zsh()
    except KeyboardInterrupt:
        log_message("用户取消操作", "WARNING")
        sys.exit(1)
    except Exception as e:
        log_message(f"连接过程出错: {str(e)}", "ERROR")
        sys.exit(1)