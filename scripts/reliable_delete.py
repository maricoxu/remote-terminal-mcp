#!/usr/bin/env python3
"""
可靠的服务器配置删除脚本
解决批量删除时的逻辑问题
"""
import yaml
import os
import json
from pathlib import Path

def load_config(config_path):
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"✅ 成功加载配置文件: {config_path}")
        return config
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        return None

def save_config(config, config_path):
    """保存配置文件"""
    try:
        # 创建备份
        backup_path = f"{config_path}.backup_{int(__import__('time').time())}"
        if os.path.exists(config_path):
            import shutil
            shutil.copy2(config_path, backup_path)
            print(f"📋 已创建备份: {backup_path}")
        
        # 保存新配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
        print(f"✅ 配置已保存到: {config_path}")
        return True
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")
        return False

def delete_servers(servers_to_delete, config_path):
    """删除指定的服务器配置"""
    print(f"\n🗑️ 开始删除服务器配置...")
    print(f"📝 目标服务器: {servers_to_delete}")
    
    # 加载配置
    config = load_config(config_path)
    if not config:
        return False
    
    # 显示删除前的服务器列表
    print(f"\n📋 删除前的服务器列表:")
    if 'servers' in config:
        for server_name in config['servers'].keys():
            status = "🎯 待删除" if server_name in servers_to_delete else "✅ 保留"
            print(f"  • {server_name} - {status}")
    else:
        print("  ⚠️ 配置中没有servers部分")
        return False
    
    # 执行删除
    deleted_count = 0
    for server_name in servers_to_delete:
        if server_name in config['servers']:
            del config['servers'][server_name]
            deleted_count += 1
            print(f"✅ 已删除: {server_name}")
        else:
            print(f"⚠️ 服务器不存在: {server_name}")
    
    # 显示删除后的服务器列表
    print(f"\n📋 删除后的服务器列表:")
    for server_name in config['servers'].keys():
        print(f"  • {server_name}")
    
    # 保存配置
    if deleted_count > 0:
        if save_config(config, config_path):
            print(f"\n🎉 成功删除 {deleted_count} 个服务器配置！")
            return True
        else:
            print(f"\n❌ 删除操作失败：无法保存配置文件")
            return False
    else:
        print(f"\n⚠️ 没有删除任何服务器配置")
        return False

if __name__ == "__main__":
    config_path = os.path.expanduser('~/.remote-terminal/config.yaml')
    servers_to_delete = ['hg-222', 'newtest']
    
    print("🚀 Remote Terminal 服务器配置删除工具")
    print("=" * 50)
    
    success = delete_servers(servers_to_delete, config_path)
    
    if success:
        print("\n✨ 删除操作完成！")
    else:
        print("\n💥 删除操作失败！") 