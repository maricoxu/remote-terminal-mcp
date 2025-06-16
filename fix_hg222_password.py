#!/usr/bin/env python3

import yaml
import os
from pathlib import Path

def fix_hg222_password():
    """修正hg222配置中的密码"""
    
    config_path = Path.home() / '.remote-terminal' / 'config.yaml'
    
    print(f"读取配置文件: {config_path}")
    
    # 读取配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 检查hg222配置
    if 'servers' in config and 'hg222' in config['servers']:
        hg222_config = config['servers']['hg222']
        
        print(f"当前密码: {hg222_config.get('password', '未设置')}")
        
        # 修正密码
        hg222_config['password'] = 'kunlunxin@yh123'
        
        print(f"修正后密码: {hg222_config['password']}")
        
        # 备份当前配置
        backup_path = config_path.with_suffix('.yaml.backup2')
        with open(backup_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        print(f"\n当前配置已备份到: {backup_path}")
        
        # 保存修正后的配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ 密码已修正并保存到: {config_path}")
        return True
    else:
        print("❌ 未找到hg222配置")
        return False

if __name__ == "__main__":
    fix_hg222_password() 