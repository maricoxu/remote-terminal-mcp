#!/usr/bin/env python3
import yaml
import os

# 使用标准配置目录
config_path = os.path.expanduser('~/.remote-terminal/config.yaml')

# 读取现有配置
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# 删除指定服务器
servers_to_remove = ['hg-222', 'newtest']
for server in servers_to_remove:
    if server in config['servers']:
        del config['servers'][server]
        print(f'✅ 已删除服务器: {server}')
    else:
        print(f'⚠️ 服务器不存在: {server}')

# 保存配置
with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

print(f'📝 配置已保存到: {config_path}')
print('\n📋 剩余服务器:')
for server_name in config['servers'].keys():
    print(f'  • {server_name}') 