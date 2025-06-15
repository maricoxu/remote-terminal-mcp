#!/usr/bin/env python3
"""
简化修复：直接修复删除服务器的逻辑
"""
import yaml
import os

def delete_servers_fixed(servers_to_delete, config_path):
    """修复版本的删除服务器功能"""
    print(f"🗑️ 开始删除服务器: {servers_to_delete}")
    
    # 加载完整配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print(f"删除前的服务器: {list(config['servers'].keys())}")
    
    # 执行删除
    deleted_count = 0
    for server_name in servers_to_delete:
        if server_name in config['servers']:
            del config['servers'][server_name]
            deleted_count += 1
            print(f"✅ 已删除: {server_name}")
        else:
            print(f"⚠️ 服务器不存在: {server_name}")
    
    print(f"删除后的服务器: {list(config['servers'].keys())}")
    
    # 直接保存完整配置（覆盖模式）
    if deleted_count > 0:
        # 创建备份
        backup_path = f"{config_path}.backup_simple_{int(__import__('time').time())}"
        import shutil
        shutil.copy2(config_path, backup_path)
        print(f"📋 已创建备份: {backup_path}")
        
        # 保存修改后的配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"🎉 成功删除 {deleted_count} 个服务器！")
        return True
    else:
        print("⚠️ 没有删除任何服务器")
        return False

if __name__ == "__main__":
    config_path = os.path.expanduser('~/.remote-terminal-mcp/config.yaml')
    
    # 测试删除功能
    print("🧪 测试删除功能...")
    
    # 先添加两个测试服务器
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 添加测试服务器
    config['servers']['test1'] = {'type': 'test', 'description': 'Test server 1'}
    config['servers']['test2'] = {'type': 'test', 'description': 'Test server 2'}
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    print("✅ 已添加测试服务器 test1, test2")
    
    # 测试删除
    success = delete_servers_fixed(['test1', 'test2'], config_path)
    
    if success:
        print("✨ 删除功能修复成功！")
    else:
        print("💥 删除功能仍有问题") 