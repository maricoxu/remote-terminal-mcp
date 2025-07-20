#!/usr/bin/env python3
"""
删除基础服务器脚本
删除指定的几台基础服务器配置
"""

import os
import yaml
from pathlib import Path

def delete_servers():
    """删除指定的基础服务器"""
    # 要删除的服务器列表
    servers_to_delete = [
        "tj09",
        "auto-interaction-test", 
        "debug_test",
        "tjdm-isa-ai-p800node10.tjdm"
    ]
    
    # 配置文件路径
    config_path = Path.home() / '.remote-terminal' / 'config.yaml'
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return
    
    # 读取现有配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if not config or 'servers' not in config:
        print("❌ 配置文件中没有servers节点")
        return
    
    # 显示删除前的服务器列表
    print("📋 删除前的服务器列表:")
    for server_name in config['servers'].keys():
        print(f"  • {server_name}")
    
    # 删除指定服务器
    deleted_servers = []
    for server_name in servers_to_delete:
        if server_name in config['servers']:
            del config['servers'][server_name]
            deleted_servers.append(server_name)
            print(f"✅ 已删除: {server_name}")
        else:
            print(f"⚠️  服务器不存在: {server_name}")
    
    if deleted_servers:
        # 创建备份
        backup_path = f"{config_path}.backup_before_delete_{int(__import__('time').time())}"
        import shutil
        shutil.copy2(config_path, backup_path)
        print(f"📋 已创建备份: {backup_path}")
        
        # 保存更新后的配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"\n🎉 成功删除 {len(deleted_servers)} 台服务器")
        
        # 显示删除后的服务器列表
        print("\n📋 删除后的服务器列表:")
        for server_name in config['servers'].keys():
            print(f"  • {server_name}")
    else:
        print("\n💡 没有服务器被删除")

if __name__ == '__main__':
    delete_servers() 