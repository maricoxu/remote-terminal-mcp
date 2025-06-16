#!/usr/bin/env python3
"""
手动复制zsh配置文件到Docker容器的脚本
"""

import subprocess
import time
import os
from pathlib import Path

def copy_zsh_config_to_container(session_name: str = "hg222_session"):
    """复制zsh配置文件到容器"""
    
    # 配置文件路径
    config_dir = Path(__file__).parent / "templates" / "configs" / "zsh"
    
    if not config_dir.exists():
        print(f"❌ 配置目录不存在: {config_dir}")
        return False
    
    print(f"📁 从配置目录复制: {config_dir}")
    
    # 复制每个配置文件
    for config_file in config_dir.glob(".*"):
        if config_file.is_file():
            print(f"📝 复制配置文件: {config_file.name}")
            
            try:
                # 读取配置文件内容
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 在容器内创建配置文件
                create_cmd = f"cat > ~/{config_file.name} << 'EOF_CONFIG_FILE'\n{content}\nEOF_CONFIG_FILE"
                
                # 发送命令到容器
                subprocess.run(['tmux', 'send-keys', '-t', session_name, create_cmd, 'Enter'],
                             capture_output=True)
                time.sleep(1)
                
                print(f"✅ 已创建: {config_file.name}")
                
            except Exception as e:
                print(f"⚠️ 处理配置文件失败: {config_file.name} - {str(e)}")
    
    # 启动zsh并应用配置
    print("🔄 启动zsh并应用配置...")
    subprocess.run(['tmux', 'send-keys', '-t', session_name, 'zsh', 'Enter'],
                 capture_output=True)
    time.sleep(2)
    
    # 重新加载zsh配置
    subprocess.run(['tmux', 'send-keys', '-t', session_name, 'source ~/.zshrc', 'Enter'],
                 capture_output=True)
    time.sleep(1)
    
    print("✅ zsh配置复制和应用完成！")
    return True

if __name__ == "__main__":
    copy_zsh_config_to_container()