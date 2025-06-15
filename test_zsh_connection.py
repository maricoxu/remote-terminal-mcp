#!/usr/bin/env python3
"""
测试zsh配置复制功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'python'))

from enhanced_ssh_manager import EnhancedSSHManager

def main():
    print("🚀 Remote Terminal - 测试zsh配置复制功能")
    print("=" * 60)
    
    # 创建SSH管理器
    manager = EnhancedSSHManager()
    
    # 显示cpu_221服务器信息（使用zsh）
    server = manager.get_server('cpu_221')
    if server:
        print(f"📋 服务器信息:")
        print(f"  名称: cpu_221")
        print(f"  地址: {server.host}")
        print(f"  用户: {server.username}")
        print(f"  类型: {server.type}")
        
        if hasattr(server, 'specs') and server.specs and 'docker' in server.specs:
            docker_config = server.specs['docker']
            print(f"  🐳 Docker配置:")
            print(f"    容器: {docker_config.get('container_name', 'N/A')}")
            print(f"    镜像: {docker_config.get('image', 'N/A')}")
            print(f"    Shell: {docker_config.get('shell', 'bash')}")
        print()
    
    # 测试zsh配置检测
    print("🔍 测试zsh配置文件检测...")
    config_source = manager._detect_config_source('zsh')
    
    if config_source:
        print(f"✅ 找到zsh配置: {config_source['type']} - {config_source['path']}")
        
        # 列出配置文件
        config_files = [f for f in os.listdir(config_source['path']) if f.startswith('.')]
        print(f"📁 配置文件: {', '.join(config_files)}")
        
        # 显示.zshrc内容预览
        zshrc_path = os.path.join(config_source['path'], '.zshrc')
        if os.path.exists(zshrc_path):
            try:
                with open(zshrc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"\n📄 .zshrc 内容预览:")
                lines = content.split('\n')[:10]
                for i, line in enumerate(lines, 1):
                    print(f"  {i:2d}: {line}")
                if len(content.split('\n')) > 10:
                    print("     ...")
            except Exception as e:
                print(f"⚠️ 无法读取.zshrc: {e}")
    else:
        print("❌ 未找到zsh配置文件")
    
    print()
    
    # 询问是否要测试连接
    print("💡 准备测试cpu_221连接和zsh配置复制...")
    print("⚠️  注意：这将创建新的连接会话")
    
    # 直接进行连接测试
    print("🔗 开始连接cpu_221...")
    success, message = manager.smart_connect('cpu_221')
    
    if success:
        print(f"✅ 连接成功: {message}")
        print("\n💡 连接提示:")
        print("  - 使用 'tmux attach -t cpu_221_session' 进入会话")
        print("  - zsh配置应该已经自动复制到容器中")
        print("  - 可以检查容器内的 ~/.zshrc 文件")
    else:
        print(f"❌ 连接失败: {message}")

if __name__ == "__main__":
    main() 