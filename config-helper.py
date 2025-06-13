#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Remote Terminal 配置助手 - 快速启动工具

使用方法:
  python config-helper.py              # 启动交互式配置管理器
  python config-helper.py --quick      # 快速配置向导
  python config-helper.py --list       # 列出现有配置
  python config-helper.py --test NAME  # 测试指定服务器连接
"""

import sys
import os
from pathlib import Path
import getpass

# 添加python目录到路径
sys.path.insert(0, str(Path(__file__).parent / "python"))

try:
    from interactive_config import InteractiveConfigManager, ServerConfig
    import yaml
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保已安装必要的依赖: pip install pyyaml")
    sys.exit(1)


def quick_setup():
    """快速配置向导"""
    print("🚀 Remote Terminal 快速配置向导")
    print("=" * 50)
    print()
    
    print("💡 这个向导将帮助您快速配置一个常用的服务器连接")
    print()
    
    # 检测常见配置模式
    print("请选择您的服务器类型:")
    print("1. 🖥️  普通Linux服务器 (直接SSH)")
    print("2. 🌉 内网服务器 (通过relay-cli)")
    print("3. 🐳 带Docker环境的开发服务器")
    print("4. 🎯 自定义配置")
    print()
    
    choice = input("请选择 (1-4): ").strip()
    
    manager = InteractiveConfigManager()
    
    if choice == "1":
        _quick_setup_ssh(manager)
    elif choice == "2":
        _quick_setup_relay(manager)
    elif choice == "3":
        _quick_setup_docker(manager)
    elif choice == "4":
        manager.create_new_server()
    else:
        print("❌ 无效选择")
        return
    
    print()
    print("✅ 快速配置完成！")
    print("💡 您可以运行以下命令连接服务器:")
    print("   python -m remote_terminal connect <服务器名称>")


def _quick_setup_ssh(manager):
    """快速设置SSH服务器"""
    print()
    print("🖥️ 配置普通SSH服务器")
    print("-" * 30)
    
    name = input("服务器名称 (如: dev-server): ").strip()
    host = input("服务器地址: ").strip()
    default_user = getpass.getuser()
    username = input(f"用户名 [{default_user}]: ").strip() or default_user
    
    config = ServerConfig(
        name=name,
        host=host,
        username=username,
        connection_type="ssh",
        description="SSH服务器",
        jump_host=""
    )
    
    manager.servers[name] = config.to_yaml_dict()
    manager._save_config()
    print(f"✅ SSH服务器 '{name}' 配置完成")


def _quick_setup_relay(manager):
    """快速设置Relay服务器"""
    print()
    print("🌉 配置内网服务器 (Relay)")
    print("-" * 30)
    
    name = input("服务器名称 (如: cpu-221): ").strip()
    target_host = input("目标服务器地址 (如: internal-server.company.com): ").strip()
    default_user = getpass.getuser()
    username = input(f"用户名 [{default_user}]: ").strip() or default_user
    
    config = ServerConfig(
        name=name,
        host="relay.example.com",  # relay服务器地址通常固定
        username=username,
        connection_type="relay",
        relay_target_host=target_host,
        jump_host="",
        description="内网服务器",
        bos_bucket=f"bos:/klx-pytorch-work-bd-bj/{getpass.getuser()}/template",
        tmux_session_prefix=name.replace('-', '').replace('_', '') + "_dev"
    )
    
    manager.servers[name] = config.to_yaml_dict()
    manager._save_config()
    print(f"✅ Relay服务器 '{name}' 配置完成")


def _quick_setup_docker(manager):
    """快速设置Docker服务器"""
    print()
    print("🐳 配置Docker开发服务器")
    print("-" * 30)
    
    name = input("服务器名称 (如: gpu-dev): ").strip()
    host = input("服务器地址: ").strip()
    default_user = getpass.getuser()
    username = input(f"用户名 [{default_user}]: ").strip() or default_user
    container = input("Docker容器名 [xyh_pytorch]: ").strip() or "xyh_pytorch"
    
    config = ServerConfig(
        name=name,
        host=host,
        username=username,
        connection_type="ssh",
        description="Docker开发服务器",
        jump_host="",
        docker_enabled=True,
        docker_container=container,
        docker_image="ubuntu:20.04",
        tmux_session_prefix=name.replace('-', '').replace('_', '') + "_dev"
    )
    
    manager.servers[name] = config.to_yaml_dict()
    manager._save_config()
    print(f"✅ Docker服务器 '{name}' 配置完成")


def list_servers():
    """列出服务器配置"""
    manager = InteractiveConfigManager()
    
    if not manager.servers:
        print("📭 暂无服务器配置")
        print("💡 运行 'python config-helper.py --quick' 快速创建配置")
        return
    
    print("📋 现有服务器配置:")
    print("=" * 50)
    
    for name, config in manager.servers.items():
        print(f"🖥️  {name}")
        print(f"   地址: {config.get('username')}@{config.get('host')}:{config.get('port', 22)}")
        
        specs = config.get('specs', {})
        connection = specs.get('connection', {})
        if connection.get('tool') == 'relay':
            target = connection.get('target', {}).get('host', '')
            print(f"   类型: Relay -> {target}")
        else:
            print(f"   类型: 直接SSH")
        
        docker = specs.get('docker', {})
        if docker:
            print(f"   Docker: {docker.get('container', 'N/A')}")
        
        print()


def test_server(server_name):
    """测试服务器连接"""
    manager = InteractiveConfigManager()
    
    if server_name not in manager.servers:
        print(f"❌ 服务器 '{server_name}' 不存在")
        print("💡 运行 'python config-helper.py --list' 查看可用服务器")
        return
    
    manager._test_server_connection(server_name)


def show_usage():
    """显示使用说明"""
    print("🚀 Remote Terminal 配置助手")
    print("=" * 50)
    print()
    print("使用方法:")
    print("  python config-helper.py              # 启动完整配置管理器")
    print("  python config-helper.py --quick      # 快速配置向导")
    print("  python config-helper.py --list       # 列出现有配置")
    print("  python config-helper.py --test NAME  # 测试服务器连接")
    print("  python config-helper.py --help       # 显示此帮助")
    print()
    print("配置文件位置:")
    manager = InteractiveConfigManager()
    print(f"  {manager.config_path}")
    print()
    print("💡 提示: 首次使用建议运行 --quick 快速创建配置")


def main():
    """主函数"""
    if len(sys.argv) == 1:
        # 无参数，启动完整配置管理器
        manager = InteractiveConfigManager()
        manager.show_main_menu()
    
    elif len(sys.argv) == 2:
        arg = sys.argv[1]
        if arg in ['--quick', '-q']:
            quick_setup()
        elif arg in ['--list', '-l']:
            list_servers()
        elif arg in ['--help', '-h']:
            show_usage()
        else:
            print(f"❌ 未知参数: {arg}")
            show_usage()
    
    elif len(sys.argv) == 3:
        if sys.argv[1] in ['--test', '-t']:
            test_server(sys.argv[2])
        else:
            print(f"❌ 未知参数: {sys.argv[1]}")
            show_usage()
    
    else:
        print("❌ 参数过多")
        show_usage()


if __name__ == "__main__":
    main()