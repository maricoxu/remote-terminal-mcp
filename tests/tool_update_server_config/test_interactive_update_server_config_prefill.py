# -*- coding: utf-8 -*-
"""
自动化回归测试：测试 update_server_config 工具的参数预填充能力
场景：用户输入『我要修改服务器hg225，它的hostname修改成192.168.1.226，用户名admin』，程序应自动预填参数，唤起交互界面，自动化输入其余参数，最终检查配置文件内容
"""
import os
import sys
import yaml
import tempfile
import shutil
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config_manager.main import EnhancedConfigManager


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

TEST_CONFIG_PATH = os.path.join(tempfile.gettempdir(), "test_config_update_server_prefill.yaml")
EXPECTED_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "expected_test_update_server_config_prefill.yaml")

# 先准备初始配置
INIT_CONFIG = {
    'servers': {
        'hg225': {
            'connection_type': 'ssh',
            'host': '192.168.1.225',
            'username': 'admin',
            'port': 22,
            'docker_enabled': False,
            'docker_config': {},
            'auto_sync_enabled': False,
            'sync_config': {},
        }
    }
}

MOCK_INPUTS = [
    "1",                      # 连接类型：1=SSH直连
    "admin@192.168.1.226",    # user@host格式（预填修改后的地址）
    "22",                     # 端口
    "4",                      # Docker模式：4=不使用Docker
    "",                       # 密码（跳过）
]

def test_interactive_update_server_config_prefill():
    # 写入初始配置
    with open(TEST_CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(INIT_CONFIG, f, allow_unicode=True)
    # 预填参数
    prefill = {
        'name': 'hg225',
        'host': '192.168.1.226',  # 修改后的host
        'username': 'admin',
    }
    with patch.object(EnhancedConfigManager, 'smart_input', side_effect=MOCK_INPUTS):
        manager = EnhancedConfigManager(config_path=TEST_CONFIG_PATH, force_interactive=True)
        manager.guided_setup(edit_server='hg225', prefill=prefill)
    # 校验配置内容
    actual = load_yaml(TEST_CONFIG_PATH)
    expected = load_yaml(EXPECTED_CONFIG_PATH)
    assert actual == expected, f"配置内容不一致\n实际: {actual}\n预期: {expected}"
    # 测试后清理
    if os.path.exists(TEST_CONFIG_PATH):
        os.remove(TEST_CONFIG_PATH)
