#!/usr/bin/env python3
"""
新增服务器配置脚本
结合 enhanced_config_manager 的功能，提供交互式配置向导
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config_manager.main import EnhancedConfigManager

def create_server_with_wizard():
    """使用向导模式创建服务器配置"""
    print("🎯 新增服务器配置 - 交互式向导")
    print("=" * 50)
    
    try:
        # 创建配置管理器
        config_manager = EnhancedConfigManager()
        
        print("\n📋 可用的配置模式:")
        print("1. 🚀 快速配置 - 2分钟完成基础SSH连接")
        print("2. 🎯 向导配置 - 逐步引导，详细配置")
        print("3. 📋 模板配置 - 基于预设模板快速配置")
        print("4. ✏️ 手动配置 - 直接编辑配置文件")
        
        choice = input("\n请选择配置模式 (1-4，默认为1): ").strip()
        if not choice:
            choice = "1"
            
        print(f"\n已选择模式: {choice}")
        
        if choice == "1":
            print("\n🚀 启动快速配置模式...")
            result = config_manager.quick_setup()
        elif choice == "2":
            print("\n🎯 启动向导配置模式...")
            result = config_manager.guided_setup()
        elif choice == "3":
            print("\n📋 启动模板配置模式...")
            result = config_manager.template_setup()
        elif choice == "4":
            print("\n✏️ 启动手动配置模式...")
            result = config_manager.manual_setup()
        else:
            print("❌ 无效选择，使用快速配置模式")
            result = config_manager.quick_setup()
            
        if result:
            print(f"\n✅ 服务器配置创建成功！")
            print(f"📁 配置文件位置: {config_manager.config_path}")
            
            # 显示创建的服务器
            try:
                servers = config_manager.get_existing_servers()
                if servers:
                    print(f"\n📊 当前配置的服务器 ({len(servers)}个):")
                    for name, config in servers.items():
                        connection_type = config.get('connection_type', config.get('type', 'unknown'))
                        host = config.get('host', 'unknown')
                        print(f"  • {name} ({connection_type}) - {host}")
            except Exception as e:
                print(f"📋 配置已保存，但无法显示服务器列表: {e}")
                
        else:
            print("❌ 服务器配置创建失败")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 配置过程出错: {e}")
        import traceback
        print(f"详细错误信息:\n{traceback.format_exc()}")
        return False

def create_server_with_params():
    """使用参数模式创建服务器配置"""
    print("🎯 新增服务器配置 - 参数模式")
    print("=" * 50)
    
    # 基本信息
    server_name = input("服务器名称: ").strip()
    if not server_name:
        print("❌ 服务器名称不能为空")
        return False
        
    host = input("服务器地址 (IP或域名): ").strip()
    if not host:
        print("❌ 服务器地址不能为空")
        return False
        
    username = input("登录用户名: ").strip()
    if not username:
        print("❌ 用户名不能为空")
        return False
    
    port = input("SSH端口 (默认22): ").strip()
    if not port:
        port = "22"
    
    # 连接类型
    print("\n连接方式:")
    print("1. SSH直连")
    print("2. Relay跳板机")
    connection_choice = input("选择连接方式 (1-2，默认1): ").strip()
    if not connection_choice:
        connection_choice = "1"
    
    connection_type = "ssh" if connection_choice == "1" else "relay"
    
    # Docker配置
    use_docker = input("\n是否启用Docker支持? (y/N): ").strip().lower() in ['y', 'yes']
    
    docker_config = {}
    if use_docker:
        docker_container = input("Docker容器名称: ").strip()
        docker_image = input("Docker镜像 (默认ubuntu:20.04): ").strip()
        if not docker_image:
            docker_image = "ubuntu:20.04"
        docker_config = {
            "container_name": docker_container or f"{server_name}_container",
            "image": docker_image
        }
    
    # 创建配置
    try:
        config_manager = EnhancedConfigManager()
        
        # 使用 mcp_guided_setup 方法
        config_params = {
            'server_name': server_name,
            'host': host,
            'username': username,
            'port': int(port),
            'connection_type': connection_type,
            'use_docker': use_docker,
            'description': f"{connection_type.upper()}连接: {server_name}"
        }
        
        if use_docker:
            config_params.update({
                'docker_image': docker_config.get('image'),
                'docker_container': docker_config.get('container_name')
            })
        
        print(f"\n📋 配置摘要:")
        for key, value in config_params.items():
            if value is not None:
                print(f"  • {key}: {value}")
        
        confirm = input("\n确认创建配置? (Y/n): ").strip().lower()
        if confirm == 'n':
            print("❌ 用户取消操作")
            return False
        
        result = config_manager.mcp_guided_setup(**config_params)
        
        if result:
            print(f"\n✅ 服务器 '{server_name}' 配置创建成功！")
            print(f"📁 配置文件: {config_manager.config_path}")
            return True
        else:
            print("❌ 配置创建失败")
            return False
            
    except Exception as e:
        print(f"❌ 创建配置时出错: {e}")
        import traceback
        print(f"详细错误信息:\n{traceback.format_exc()}")
        return False

def main():
    """主函数"""
    print("🚀 远程终端MCP - 服务器配置管理")
    print("=" * 50)
    
    # 检查配置目录
    config_path = Path.home() / '.remote-terminal' / 'config.yaml'
    print(f"📁 配置文件路径: {config_path}")
    
    if config_path.exists():
        print("✅ 配置文件已存在")
    else:
        print("📝 配置文件不存在，将创建新的配置")
    
    print("\n选择创建方式:")
    print("1. 🎯 交互式向导 (推荐)")
    print("2. 📝 参数输入模式")
    print("3. 🔍 查看现有配置")
    
    mode = input("\n请选择 (1-3，默认为1): ").strip()
    if not mode:
        mode = "1"
    
    if mode == "1":
        return create_server_with_wizard()
    elif mode == "2":
        return create_server_with_params()
    elif mode == "3":
        try:
            config_manager = EnhancedConfigManager()
            servers = config_manager.get_existing_servers()
            
            if servers:
                print(f"\n📊 现有服务器配置 ({len(servers)}个):")
                for name, config in servers.items():
                    connection_type = config.get('connection_type', config.get('type', 'unknown'))
                    host = config.get('host', 'unknown')
                    username = config.get('username', config.get('user', 'unknown'))
                    description = config.get('description', '无描述')
                    print(f"\n🖥️  服务器: {name}")
                    print(f"   地址: {host}")
                    print(f"   用户: {username}")
                    print(f"   类型: {connection_type}")
                    print(f"   描述: {description}")
            else:
                print("\n📋 没有找到服务器配置")
            return True
        except Exception as e:
            print(f"❌ 查看配置时出错: {e}")
            return False
    else:
        print("❌ 无效选择")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n🛑 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        print(f"详细错误信息:\n{traceback.format_exc()}")
        sys.exit(1) 