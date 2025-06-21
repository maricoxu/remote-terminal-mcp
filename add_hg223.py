#!/usr/bin/env python3
import yaml
import os

# 使用标准配置目录而不是硬编码的.remote-terminal-mcp
config_path = os.path.expanduser('~/.remote-terminal/config.yaml')

# 读取现有配置
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# 添加hg223配置
config['servers']['hg223'] = {
    'connection_type': 'relay',
    'description': 'Relay连接: hg223',
    'host': 'szzj-isa-ai-peking-poc06.szzj',
    'password': 'kunlunxin@yh123',
    'port': 22,
    'private_key_path': '~/.ssh/id_rsa',
    'session': {
        'name': 'hg223_session',
        'shell': '/bin/bash',
        'working_directory': '~'
    },
    'specs': {
        'connection': {
            'jump_host': {
                'host': '10.129.130.223',
                'username': 'root'
            },
            'target': {
                'host': 'szzj-isa-ai-peking-poc06.szzj'
            },
            'tool': 'relay-cli'
        },
        'docker': {
            'auto_create': True,
            'container_name': 'xyh_pytorch',
            'image': 'iregistry.baidu-int.com/xmlir/xmlir_ubuntu_2004_x86_64:v0.32',
            'ports': ['8080:8080', '8888:8888', '6006:6006'],
            'volumes': ['/home:/home', '/data:/data']
        }
    },
    'type': 'script_based',
    'username': 'yh'
}

# 保存配置
with open(config_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

print('✅ hg223服务器配置已添加成功！')
print(f'📝 配置文件位置: {config_path}') 