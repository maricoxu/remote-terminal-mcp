#!/usr/bin/env python3

import yaml
import os
from pathlib import Path

def migrate_hg222_password():
    """将hg222主配置中的密码迁移到跳板机配置中"""
    
    config_path = Path.home() / '.remote-terminal' / 'config.yaml'
    
    print(f"读取配置文件: {config_path}")
    
    # 读取配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 检查hg222配置
    if 'servers' in config and 'hg222' in config['servers']:
        hg222_config = config['servers']['hg222']
        
        print("当前hg222配置:")
        print(f"  主配置密码: {hg222_config.get('password', '未设置')}")
        
        # 获取主配置中的密码
        main_password = hg222_config.get('password')
        
        if main_password:
            # 确保specs结构存在
            if 'specs' not in hg222_config:
                hg222_config['specs'] = {'connection': {}}
            elif 'connection' not in hg222_config['specs']:
                hg222_config['specs']['connection'] = {}
            
            # 确保jump_host结构存在
            if 'jump_host' not in hg222_config['specs']['connection']:
                hg222_config['specs']['connection']['jump_host'] = {}
            
            # 将密码迁移到跳板机配置
            hg222_config['specs']['connection']['jump_host']['password'] = main_password
            
            # 删除主配置中的密码
            del hg222_config['password']
            
            print(f"✅ 密码已迁移到跳板机配置")
            print(f"✅ 主配置密码已删除")
        else:
            print("❌ 主配置中没有找到密码")
            return
        
        # 备份当前配置
        backup_path = config_path.with_suffix('.yaml.backup3')
        with open(backup_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
        print(f"✅ 配置已备份到: {backup_path}")
        
        # 保存修改后的配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        print(f"✅ 配置已更新")
        
        # 显示更新后的配置
        print("\n更新后的hg222配置:")
        jump_host = hg222_config['specs']['connection'].get('jump_host', {})
        print(f"  跳板机密码: {jump_host.get('password', '未设置')}")
        print(f"  主配置密码: {hg222_config.get('password', '未设置')}")
        
    else:
        print("❌ 未找到hg222配置")

if __name__ == "__main__":
    migrate_hg222_password() 