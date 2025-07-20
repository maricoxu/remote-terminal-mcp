#!/usr/bin/env python3
"""
测试增强的服务器列表功能
"""

import sys
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config_manager.main import EnhancedConfigManager
from python.enhanced_ssh_manager import create_enhanced_manager

def test_enhanced_list():
    """测试增强的服务器列表功能"""
    print("🧪 测试增强的服务器列表功能\n")
    
    try:
        # 创建管理器
        config_manager = EnhancedConfigManager()
        ssh_manager = create_enhanced_manager()
        
        # 从配置管理器获取完整配置
        all_servers = config_manager.get_existing_servers()
        print(f"✅ 找到 {len(all_servers)} 个服务器配置")
        
        # 测试第一个服务器的详细信息
        if all_servers:
            server_name = list(all_servers.keys())[0]
            server_config = all_servers[server_name]
            print(f"\n🔍 测试服务器: {server_name}")
            print(f"   配置类型: {server_config.get('connection_type')}")
            print(f"   主机: {server_config.get('host')}")
            print(f"   用户: {server_config.get('username')}")
            
            # 检查specs
            specs = server_config.get('specs', {})
            if specs:
                print(f"   Specs: {list(specs.keys())}")
                
                # Docker信息
                docker_config = specs.get('docker', {})
                if docker_config:
                    print(f"   Docker镜像: {docker_config.get('image', 'N/A')}")
                    print(f"   容器名: {docker_config.get('container_name', 'N/A')}")
                
                # 连接信息
                connection_specs = specs.get('connection', {})
                if connection_specs:
                    print(f"   连接工具: {connection_specs.get('tool', 'N/A')}")
                    jump_host = connection_specs.get('jump_host', {})
                    if jump_host:
                        print(f"   跳板: {jump_host.get('username')}@{jump_host.get('host')}")
            
        print("\n✅ 测试完成！")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_list()
