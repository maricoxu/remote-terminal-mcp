#!/usr/bin/env python3
"""
Script-based连接调试工具
"""

import subprocess
import time
import sys
import os
from ssh_manager import SSHManager

class ScriptConnectionDebugger:
    """Script连接调试器"""
    
    def __init__(self):
        self.manager = SSHManager()
        self.session_name = "cpu221_dev"
        
    def debug_session_status(self):
        """调试会话状态"""
        print("🔍 调试会话状态\n")
        
        # 1. 检查会话是否存在
        print("1️⃣ 检查tmux会话:")
        result = subprocess.run(['tmux', 'has-session', '-t', self.session_name], 
                              capture_output=True)
        if result.returncode == 0:
            print(f"   ✅ 会话 {self.session_name} 存在")
        else:
            print(f"   ❌ 会话 {self.session_name} 不存在")
            return
            
        # 2. 获取会话详细信息
        print(f"\n2️⃣ 会话详细信息:")
        result = subprocess.run(['tmux', 'list-sessions', '-F', 
                               '#{session_name}: #{session_windows} windows, created #{session_created}, #{?session_attached,attached,not attached}'], 
                              capture_output=True, text=True)
        for line in result.stdout.strip().split('\n'):
            if self.session_name in line:
                print(f"   📋 {line}")
        
        # 3. 查看当前窗口状态
        print(f"\n3️⃣ 当前窗口状态:")
        result = subprocess.run(['tmux', 'list-windows', '-t', self.session_name, '-F',
                               '#{window_index}: #{window_name} #{window_panes} panes #{?window_active,*active,}'],
                              capture_output=True, text=True)
        print(f"   📋 {result.stdout.strip()}")
        
        # 4. 捕获完整屏幕内容
        print(f"\n4️⃣ 当前屏幕内容:")
        result = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                              capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        for i, line in enumerate(lines[-20:], 1):  # 显示最后20行
            print(f"   {i:2d}| {line}")
    
    def test_available_commands(self):
        """测试可用命令"""
        print("\n🧪 测试受限环境中的可用命令\n")
        
        # 基本命令测试列表
        test_commands = [
            # 基本路径命令
            ("/bin/echo 'test'", "完整路径echo"),
            ("/usr/bin/whoami", "完整路径whoami"),
            ("/bin/pwd", "完整路径pwd"),
            ("/bin/ls", "完整路径ls"),
            
            # 内建命令
            ("type echo", "检查echo类型"),
            ("which bash", "查找bash位置"),
            ("env", "环境变量"),
            ("set", "shell变量"),
            
            # 系统信息
            ("/bin/uname -a", "系统信息"),
            ("/usr/bin/id", "用户ID"),
            
            # 文件系统
            ("/bin/ls /", "根目录列表"),
            ("/bin/ls /usr/bin | head", "usr/bin目录"),
            
            # 进程和系统
            ("/bin/ps", "进程列表"),
            ("jobs", "当前任务"),
            
            # Docker相关
            ("/usr/bin/docker --version", "Docker版本"),
            ("command -v docker", "查找docker命令"),
            
            # 网络
            ("/bin/netstat -rn", "路由表"),
            ("/sbin/ifconfig", "网络接口"),
        ]
        
        results = []
        for cmd, desc in test_commands:
            print(f"🔍 测试: {desc}")
            print(f"    命令: {cmd}")
            
            # 在tmux会话中执行命令
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, cmd, 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            # 捕获输出
            result = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                                  capture_output=True, text=True)
            
            # 分析结果
            output_lines = result.stdout.strip().split('\n')
            last_line = output_lines[-1] if output_lines else ""
            
            if "command not found" in result.stdout:
                status = "❌ 不可用"
            elif "restricted" in result.stdout:
                status = "🚫 受限"
            elif "Permission denied" in result.stdout:
                status = "🔒 权限拒绝"
            elif cmd in last_line:  # 命令还在提示符中，未执行完成
                status = "⏳ 执行中"
            else:
                status = "✅ 可用"
            
            print(f"    结果: {status}")
            results.append((cmd, desc, status, result.stdout[-200:]))  # 保存最后200字符
            print()
        
        return results
    
    def interactive_debug(self):
        """交互式调试"""
        print("\n🎮 交互式调试模式")
        print("你可以直接输入命令到远程会话中进行测试")
        print("输入 'exit_debug' 退出调试模式\n")
        
        while True:
            try:
                cmd = input(f"🖥️  [{self.session_name}] $ ").strip()
                
                if cmd == 'exit_debug':
                    print("🚪 退出调试模式")
                    break
                elif cmd == '':
                    continue
                elif cmd == 'capture':
                    # 捕获当前屏幕
                    result = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                                          capture_output=True, text=True)
                    print("📺 当前屏幕内容:")
                    for line in result.stdout.strip().split('\n')[-10:]:
                        print(f"   {line}")
                    continue
                
                # 发送命令到tmux会话
                subprocess.run(['tmux', 'send-keys', '-t', self.session_name, cmd, 'Enter'],
                             capture_output=True)
                
                # 等待执行
                time.sleep(1)
                
                # 获取响应（最后几行）
                result = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                                      capture_output=True, text=True)
                lines = result.stdout.strip().split('\n')
                
                # 显示最后的输出
                print("📤 输出:")
                for line in lines[-5:]:
                    print(f"   {line}")
                print()
                
            except KeyboardInterrupt:
                print("\n🚪 退出调试模式")
                break
            except Exception as e:
                print(f"❌ 错误: {e}")
    
    def create_debug_script(self):
        """创建原始连接脚本用于对比"""
        script_content = '''#!/bin/bash
# 模拟原始connect_cpu_221.sh脚本的连接过程

echo "🚀 启动relay-cli连接..."
relay-cli

echo "🎯 连接到目标服务器..."
ssh bjhw-sys-rpm0221.bjhw

echo "🐳 尝试进入Docker容器..."
docker exec -it xyh_pytorch bash

echo "📁 设置工作目录..."
cd /home/xuyehua

echo "✅ 连接建立完成"
'''
        
        script_path = "debug_connect_cpu221.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
        print(f"📝 已创建调试脚本: {script_path}")
        print(f"   可以手动运行对比: ./{script_path}")
        
        return script_path
    
    def suggest_improvements(self, test_results):
        """基于测试结果提供改进建议"""
        print("\n💡 改进建议:")
        
        available_commands = [r for r in test_results if "✅" in r[2]]
        
        if available_commands:
            print("\n✅ 可用命令:")
            for cmd, desc, status, _ in available_commands:
                print(f"   • {cmd} - {desc}")
        
        print(f"\n🔧 针对受限环境的优化建议:")
        print(f"   1. 使用完整路径的命令 (/bin/echo, /usr/bin/whoami)")
        print(f"   2. 避免使用重定向和管道")
        print(f"   3. 使用内建命令替代外部命令")
        print(f"   4. 检查是否有替代的命令路径")
        
        print(f"\n📋 代码优化方向:")
        print(f"   • 在_establish_script_based_connection中使用完整路径命令")
        print(f"   • 增加命令可用性检测")
        print(f"   • 提供受限环境的命令映射")

def main():
    """主函数"""
    debugger = ScriptConnectionDebugger()
    
    print("🔧 Script-based连接调试工具")
    print("="*50)
    
    while True:
        print("\n📋 调试选项:")
        print("1. 查看会话状态")
        print("2. 测试可用命令")
        print("3. 交互式调试")
        print("4. 创建对比脚本")
        print("5. 退出")
        
        try:
            choice = input("\n请选择 (1-5): ").strip()
            
            if choice == '1':
                debugger.debug_session_status()
            elif choice == '2':
                results = debugger.test_available_commands()
                debugger.suggest_improvements(results)
            elif choice == '3':
                debugger.interactive_debug()
            elif choice == '4':
                debugger.create_debug_script()
            elif choice == '5':
                print("🚪 退出调试工具")
                break
            else:
                print("❌ 无效选择，请输入1-5")
                
        except KeyboardInterrupt:
            print("\n🚪 退出调试工具")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")

if __name__ == "__main__":
    main() 