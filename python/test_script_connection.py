#!/usr/bin/env python3
"""
测试script_based连接功能
"""

from ssh_manager import SSHManager
import sys
import os

def main():
    print("🧪 测试script_based连接功能\n")
    
    # 创建SSH管理器
    manager = SSHManager()
    
    # 测试远程服务器
    server_name = "remote-server"
    
    print(f"1️⃣ 测试连接到 {server_name}...")
    success, message = manager.test_connection(server_name)
    print(f"   结果: {'✅' if success else '❌'} {message}\n")
    
    if success:
        print("2️⃣ 测试命令执行...")
        success, output = manager.execute_command(server_name, "pwd")
        print(f"   结果: {'✅' if success else '❌'}")
        print(f"   输出:\n{output}\n")
        
        if success:
            print("3️⃣ 测试环境信息...")
            success, output = manager.execute_command(server_name, "echo 'Remote Environment:' && whoami && hostname")
            print(f"   结果: {'✅' if success else '❌'}")
            print(f"   输出:\n{output}\n")
    else:
        print("❌ 连接失败，跳过后续测试")
    
    # 显示服务器状态
    print("4️⃣ 服务器状态:")
    status = manager.get_server_status(server_name)
    for key, value in status.items():
        print(f"   {key}: {value}")

if __name__ == "__main__":
    main() 