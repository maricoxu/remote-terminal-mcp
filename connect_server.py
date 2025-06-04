#!/usr/bin/env python3
"""
独立服务器连接脚本

用法:
  python3 connect_server.py hg-222
  python3 connect_server.py hg-222 --force-recreate
  python3 connect_server.py --list
"""

import sys
import argparse
import os
from pathlib import Path

# 添加python目录到路径
script_dir = Path(__file__).parent
sys.path.append(str(script_dir / "python"))

try:
    from ssh_manager import SSHManager
except ImportError as e:
    print(f"❌ 无法导入SSH管理器: {e}")
    print("请确认在remote-terminal-mcp目录下运行此脚本")
    sys.exit(1)


def list_servers(manager):
    """列出所有可用服务器"""
    print("🖥️ 可用服务器列表:")
    print("=" * 50)
    
    servers = manager.list_servers()
    if not servers:
        print("📭 没有配置任何服务器")
        print("\n💡 请编辑配置文件: ~/.remote-terminal-mcp/config.yaml")
        return
    
    for server in servers:
        status_icon = "🟢" if server['connected'] else "🔴"
        print(f"{status_icon} {server['name']:<15} ({server['type']})")
        print(f"   📍 {server['host']}")
        print(f"   📝 {server['description']}")
        
        # 显示跳板机信息
        if server.get('jump_host'):
            print(f"   🔗 跳板机: {server['jump_host']}")
        
        print()


def connect_server(manager, server_name, force_recreate=False):
    """连接到指定服务器"""
    print(f"🚀 连接到服务器: {server_name}")
    print("=" * 50)
    
    # 获取服务器配置
    server = manager.get_server(server_name)
    if not server:
        print(f"❌ 服务器 '{server_name}' 不存在")
        print("\n📋 可用服务器:")
        available_servers = [s['name'] for s in manager.list_servers()]
        for name in available_servers:
            print(f"   • {name}")
        return False
    
    print(f"📍 服务器信息: {server.description}")
    print(f"🔧 连接类型: {server.type}")
    
    # 检查session
    if hasattr(server, 'session') and server.session:
        session_name = server.session.get('name', f"{server_name}_dev")
    else:
        session_name = f"{server_name}_dev"
    print(f"📋 Session名称: {session_name}")
    
    if force_recreate:
        print(f"🔄 强制重建session...")
        import subprocess
        subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
    
    # 建立连接
    print(f"\n🔗 开始建立连接...")
    try:
        success, message = manager._establish_script_based_connection(server)
        
        if success:
            print(f"✅ 连接建立成功!")
            print(f"📝 详情: {message}")
            print(f"\n🎯 连接命令:")
            print(f"tmux attach -t {session_name}")
            print(f"\n💡 快速操作:")
            print(f"• 连接: tmux attach -t {session_name}")
            print(f"• 分离: Ctrl+B, 然后按 D")
            print(f"• 查看: tmux list-sessions")
            return True
        else:
            print(f"❌ 连接失败:")
            print(f"📝 错误: {message}")
            
            # 提供诊断建议
            print(f"\n🔧 诊断建议:")
            if "connection timed out" in message.lower():
                print("• 检查网络连接和服务器地址")
                print("• 验证跳板机地址是否正确")
            elif "permission denied" in message.lower():
                print("• 检查用户名和密码")
                print("• 验证SSH密钥配置")
            elif "password" in message.lower():
                print("• 检查配置文件中的密码设置")
                print("• 确认目标服务器密码正确")
            else:
                print("• 检查服务器配置")
                print("• 验证网络连接")
                print("• 确认目标服务器状态")
            
            return False
            
    except Exception as e:
        print(f"❌ 连接过程异常: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Remote Terminal 服务器连接工具")
    parser.add_argument("server_name", nargs="?", help="要连接的服务器名称")
    parser.add_argument("--list", action="store_true", help="列出所有可用服务器")
    parser.add_argument("--force-recreate", action="store_true", help="强制重新创建session")
    parser.add_argument("--test", action="store_true", help="仅测试连接，不建立session")
    
    args = parser.parse_args()
    
    # 初始化SSH管理器
    try:
        print("🔧 初始化SSH管理器...")
        manager = SSHManager()
        print("✅ SSH管理器初始化成功")
    except Exception as e:
        print(f"❌ SSH管理器初始化失败: {e}")
        print("💡 请检查配置文件: ~/.remote-terminal-mcp/config.yaml")
        sys.exit(1)
    
    # 处理命令
    if args.list:
        list_servers(manager)
    elif args.server_name:
        if args.test:
            print(f"🧪 测试连接到: {args.server_name}")
            success, message = manager.test_connection(args.server_name)
            if success:
                print(f"✅ 连接测试成功: {message}")
            else:
                print(f"❌ 连接测试失败: {message}")
        else:
            success = connect_server(manager, args.server_name, args.force_recreate)
            sys.exit(0 if success else 1)
    else:
        print("❌ 请指定服务器名称或使用 --list 查看可用服务器")
        print("\n用法示例:")
        print("  python3 connect_server.py hg-222")
        print("  python3 connect_server.py hg-222 --force-recreate")
        print("  python3 connect_server.py --list")
        print("  python3 connect_server.py hg-222 --test")
        sys.exit(1)


if __name__ == "__main__":
    main() 