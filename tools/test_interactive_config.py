#!/usr/bin/env python3
"""
测试强制交互模式的配置管理器
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config_manager.main import EnhancedConfigManager

def test_force_interactive():
    """测试强制交互模式"""
    print("🎯 测试强制交互模式")
    print("=" * 50)
    
    # 模拟MCP环境
    os.environ['NO_COLOR'] = '1'
    
    print("1. 测试普通模式（应该禁用交互）")
    manager1 = EnhancedConfigManager()
    print(f"   is_mcp_mode: {manager1.is_mcp_mode}")
    print(f"   force_interactive: {manager1.force_interactive}")
    print(f"   interactive_mode_enabled: {manager1.interactive_mode_enabled}")
    
    print("\n2. 测试强制交互模式（应该启用交互）")
    manager2 = EnhancedConfigManager(force_interactive=True)
    print(f"   is_mcp_mode: {manager2.is_mcp_mode}")
    print(f"   force_interactive: {manager2.force_interactive}")
    print(f"   interactive_mode_enabled: {manager2.interactive_mode_enabled}")
    
    print("\n3. 测试colored_print方法")
    print("   普通模式输出:")
    manager1.colored_print("这条消息应该被抑制")
    print("   强制交互模式输出:")
    manager2.colored_print("这条消息应该显示")
    
    print("\n4. 测试smart_input方法")
    print("   普通模式输入（应该返回默认值）:")
    result1 = manager1.smart_input("请输入服务器名称: ", default="test_server")
    print(f"   结果: {result1}")
    
    print("   强制交互模式输入（应该提示用户输入）:")
    result2 = manager2.smart_input("请输入服务器名称: ", default="test_server")
    print(f"   结果: {result2}")

if __name__ == "__main__":
    test_force_interactive() 