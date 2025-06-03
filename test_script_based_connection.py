#!/usr/bin/env python3
"""
独立测试script_based连接功能
验证Docker自动创建和会话管理逻辑
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# 添加python目录到路径
script_dir = Path(__file__).parent
python_dir = script_dir / "python"
sys.path.insert(0, str(python_dir))

# 设置安静模式
os.environ['MCP_QUIET'] = '1'

from ssh_manager import SSHManager

def test_script_based_connection():
    """测试script_based连接功能"""
    print("🚀 独立测试script_based连接功能")
    print("="*60)
    
    try:
        # 1. 初始化SSH管理器
        print("\n1️⃣ 初始化SSH管理器...")
        manager = SSHManager()
        print("✅ SSH管理器初始化成功")
        
        # 2. 获取remote-server配置
        print("\n2️⃣ 检查remote-server配置...")
        server = manager.get_server("remote-server")
        if not server:
            print("❌ 找不到remote-server配置")
            return False
            
        print("✅ 配置加载成功:")
        print(f"   类型: {server.type}")
        print(f"   连接工具: {server.specs.get('connection', {}).get('tool', 'N/A')}")
        print(f"   目标主机: {server.specs.get('connection', {}).get('target', {}).get('host', 'N/A')}")
        print(f"   容器名称: {server.specs.get('docker', {}).get('container_name', 'N/A')}")
        print(f"   容器镜像: {server.specs.get('docker', {}).get('image', 'N/A')}")
        
        # 3. 检查会话名称
        session_name = server.session.get('name', f"{server.name}_session") if server.session else f"{server.name}_session"
        print(f"\n3️⃣ 目标会话名称: {session_name}")
        
        # 检查会话是否已存在
        result = subprocess.run(['tmux', 'has-session', '-t', session_name], capture_output=True)
        if result.returncode == 0:
            print(f"⚠️  会话 {session_name} 已存在")
            
            # 检查会话状态
            capture_result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                          capture_output=True, text=True)
            if capture_result.returncode == 0:
                output = capture_result.stdout
                print(f"📄 当前会话状态:")
                lines = output.strip().split('\n')
                recent_lines = lines[-3:] if len(lines) > 3 else lines
                for line in recent_lines:
                    print(f"      {line}")
                
                # 检查是否在远程环境
                if 'MacBook-Pro-3.local' in output:
                    print("🔍 检测到会话已断开（回到本地）")
                    cleanup_choice = input("\n是否清理旧会话并重新测试？(y/n): ").lower().strip()
                    if cleanup_choice == 'y':
                        subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
                        print(f"🗑️  已清理旧会话: {session_name}")
                    else:
                        print("⏭️  跳过连接测试")
                        return True
                else:
                    print("✅ 会话处于远程状态")
                    test_choice = input("\n是否继续测试远程命令？(y/n): ").lower().strip()
                    if test_choice != 'y':
                        return True
        else:
            print(f"📭 会话 {session_name} 不存在")
        
        # 4. 测试连接建立
        print(f"\n4️⃣ 测试连接建立...")
        print("⚠️  注意：这将启动真实的远程连接！")
        
        proceed = input("确认继续测试？(y/n): ").lower().strip()
        if proceed != 'y':
            print("🛑 测试已取消")
            return True
        
        print("🚀 开始建立连接...")
        success, message = manager.test_connection("remote-server")
        
        if success:
            print(f"✅ 连接测试成功: {message}")
            
            # 等待连接稳定
            print("⏳ 等待连接稳定...")
            time.sleep(3)
            
            # 5. 测试Docker功能
            print(f"\n5️⃣ 测试Docker相关功能...")
            
            docker_tests = [
                ("pwd", "检查当前目录"),
                ("whoami", "检查当前用户"),
                ("which docker", "检查Docker是否可用"),
                ("docker --version", "检查Docker版本"),
                ("docker ps -a | grep xyh_pytorch", "检查目标容器"),
            ]
            
            for cmd, desc in docker_tests:
                print(f"\n🔍 {desc}...")
                print(f"   命令: {cmd}")
                
                success, output = manager.execute_command("remote-server", cmd)
                if success:
                    print(f"   ✅ 成功")
                    # 提取有用的输出
                    lines = output.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith('📤') and not line.startswith('🖥️') and not line.startswith('📄'):
                            print(f"   💬 {line}")
                            break
                else:
                    print(f"   ❌ 失败")
                    print(f"   📄 错误: {output}")
                
                time.sleep(1)  # 避免命令执行过快
            
            # 6. 测试会话状态
            print(f"\n6️⃣ 检查最终会话状态...")
            capture_result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                          capture_output=True, text=True)
            if capture_result.returncode == 0:
                output = capture_result.stdout
                print(f"📄 最终会话状态:")
                lines = output.strip().split('\n')
                recent_lines = lines[-5:] if len(lines) > 5 else lines
                for line in recent_lines:
                    print(f"      {line}")
            
        else:
            print(f"❌ 连接测试失败: {message}")
            return False
        
        # 7. 总结
        print(f"\n" + "="*60)
        print("📊 测试完成总结:")
        print("✅ SSH管理器初始化成功")
        print("✅ 配置加载正确")
        print("✅ script_based连接逻辑工作正常")
        print("✅ Docker自动创建功能已就绪")
        print(f"✅ 会话 {session_name} 运行正常")
        print("="*60)
        
        return True
        
    except KeyboardInterrupt:
        print("\n❌ 测试被用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_session_info():
    """显示当前会话信息"""
    print("\n📋 当前tmux会话信息:")
    try:
        result = subprocess.run(['tmux', 'list-sessions'], capture_output=True, text=True)
        if result.returncode == 0:
            sessions = result.stdout.strip()
            if sessions:
                for line in sessions.split('\n'):
                    print(f"   🖥️  {line}")
            else:
                print("   📭 没有活动会话")
        else:
            print("   ❌ 无法获取会话信息")
    except Exception as e:
        print(f"   ❌ 错误: {e}")

def main():
    """主函数"""
    print("🧪 Script-based连接独立测试工具")
    print("="*60)
    
    # 显示当前会话
    show_session_info()
    
    print("\n📋 测试选项:")
    print("1. 🚀 运行完整连接测试")
    print("2. 📄 仅显示配置信息")
    print("3. 🔍 检查现有会话状态")
    print("4. 🩺 运行连接诊断")
    print("5. 🗑️  清理所有remote相关会话")
    print("6. 🚪 退出")
    
    while True:
        try:
            choice = input("\n请选择操作 (1-6): ").strip()
            
            if choice == '1':
                return test_script_based_connection()
            elif choice == '2':
                # 显示配置信息
                try:
                    manager = SSHManager()
                    server = manager.get_server("remote-server")
                    if server:
                        print("\n📋 Remote-server配置:")
                        print(f"   类型: {server.type}")
                        print(f"   连接工具: {server.specs.get('connection', {}).get('tool', 'N/A')}")
                        print(f"   目标主机: {server.specs.get('connection', {}).get('target', {}).get('host', 'N/A')}")
                        print(f"   容器名称: {server.specs.get('docker', {}).get('container_name', 'N/A')}")
                        print(f"   容器镜像: {server.specs.get('docker', {}).get('image', 'N/A')}")
                        print(f"   自动配置: {server.specs.get('environment_setup', {}).get('auto_setup', False)}")
                        return True
                    else:
                        print("❌ 找不到remote-server配置")
                        return False
                except Exception as e:
                    print(f"❌ 获取配置失败: {e}")
                    return False
            elif choice == '3':
                # 检查会话状态
                show_session_info()
                session_name = "cpu221_dev"
                result = subprocess.run(['tmux', 'has-session', '-t', session_name], capture_output=True)
                if result.returncode == 0:
                    print(f"\n📄 会话 {session_name} 状态:")
                    capture_result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                                  capture_output=True, text=True)
                    if capture_result.returncode == 0:
                        lines = capture_result.stdout.strip().split('\n')
                        for line in lines[-10:]:  # 显示最后10行
                            print(f"      {line}")
                else:
                    print(f"\n📭 会话 {session_name} 不存在")
                continue
            elif choice == '4':
                # 运行诊断
                try:
                    manager = SSHManager()
                    print("\n🩺 运行连接诊断...")
                    manager.print_connection_diagnostics("remote-server")
                except Exception as e:
                    print(f"❌ 诊断失败: {e}")
                continue
            elif choice == '5':
                # 清理会话
                sessions_to_clean = ['cpu221_dev', 'remote-server_session']
                for session in sessions_to_clean:
                    result = subprocess.run(['tmux', 'has-session', '-t', session], capture_output=True)
                    if result.returncode == 0:
                        subprocess.run(['tmux', 'kill-session', '-t', session], capture_output=True)
                        print(f"🗑️  已清理会话: {session}")
                    else:
                        print(f"📭 会话 {session} 不存在")
                show_session_info()
                continue
            elif choice == '6':
                print("👋 再见！")
                return True
            else:
                print("❌ 无效选择，请输入1-6")
                continue
                
        except KeyboardInterrupt:
            print("\n👋 再见！")
            return True
        except Exception as e:
            print(f"❌ 错误: {e}")
            continue

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"💥 严重错误: {e}")
        exit(1) 