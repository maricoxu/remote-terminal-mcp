#!/usr/bin/env python3
"""
Enhanced连接脚本 - 使用enhanced SSH manager连接服务器并自动应用配置
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'python'))

from enhanced_ssh_manager import create_enhanced_manager

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("使用方法: python3 enhanced_connect.py <服务器名称>")
        print("例如: python3 enhanced_connect.py hg222")
        sys.exit(1)
    
    server_name = sys.argv[1]
    
    print(f"🚀 开始连接服务器: {server_name}")
    
    try:
        # 创建enhanced SSH manager
        manager = create_enhanced_manager()
        
        # 智能连接
        success, message = manager.smart_connect(server_name, force_recreate=True)
        
        if success:
            print(f"✅ 连接成功: {message}")
            print(f"💡 使用以下命令进入会话: tmux attach -t {server_name}_session")
        else:
            print(f"❌ 连接失败: {message}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 连接过程出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()