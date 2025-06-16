#!/usr/bin/env python3

import yaml
import os
from pathlib import Path

def fix_hg222_config():
    """修正hg222配置中的jump_host和target顺序"""
    
    config_path = Path.home() / '.remote-terminal' / 'config.yaml'
    
    print(f"读取配置文件: {config_path}")
    
    # 读取配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 检查hg222配置
    if 'servers' in config and 'hg222' in config['servers']:
        hg222_config = config['servers']['hg222']
        
        print("当前hg222配置:")
        print(f"  jump_host: {hg222_config['specs']['connection']['jump_host']}")
        print(f"  target: {hg222_config['specs']['connection']['target']}")
        
        # 交换jump_host和target
        old_jump_host = hg222_config['specs']['connection']['jump_host']
        old_target = hg222_config['specs']['connection']['target']
        
        # 修正配置
        hg222_config['specs']['connection']['jump_host'] = {
            'host': old_target['host'],  # szzj-isa-ai-peking-poc06.szzj
            'username': 'yh'  # 使用yh用户连接跳板机
        }
        
        hg222_config['specs']['connection']['target'] = {
            'host': old_jump_host['host'],  # 10.129.130.222
            'username': old_jump_host['username']  # root
        }
        
        print("\n修正后的配置:")
        print(f"  jump_host: {hg222_config['specs']['connection']['jump_host']}")
        print(f"  target: {hg222_config['specs']['connection']['target']}")
        
        # 备份原配置
        backup_path = config_path.with_suffix('.yaml.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        print(f"\n原配置已备份到: {backup_path}")
        
        # 保存修正后的配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ 配置已修正并保存到: {config_path}")
        return True
    else:
        print("❌ 未找到hg222配置")
        return False

if __name__ == "__main__":
    fix_hg222_config() 