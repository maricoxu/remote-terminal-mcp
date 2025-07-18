# -*- coding: utf-8 -*-
"""
自动化回归测试：测试 update_server_config 工具的交互式修改服务器配置能力
场景：用户输入『我要修改服务器cpu_221配置』，程序应自动检测服务器存在，唤起交互界面，自动化输入修改参数，最终检查配置文件内容
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

TEST_CONFIG_PATH = os.path.join(tempfile.gettempdir(), "test_config_update_server.yaml")
EXPECTED_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../expected/test_update_server_config.yaml")

# 先准备初始配置
INIT_CONFIG = {
    'servers': {
        'cpu_221': {
            'host': '10.0.0.221',
            'username': 'root',
            'port': 22,
            'docker_enabled': False,
            'docker_config': {},
            'auto_sync_enabled': False,
            'sync_config': {},
        }
    }
}

MOCK_INPUTS = [
    "",  # 服务器名称（已预填）
    "",  # 服务器地址（已预填）
    "",  # 端口（直接回车用默认22）
    "2", # 是否启用docker
    "2", # 是否启用自动同步
    "", "", "", "", "",  # 预留给后续所有可选/确认输入
]

def test_interactive_update_server_config():
    # 写入初始配置
    with open(TEST_CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(INIT_CONFIG, f, allow_unicode=True)
    # 自动化交互
    with patch("builtins.input", side_effect=MOCK_INPUTS):
        manager = EnhancedConfigManager(config_path=TEST_CONFIG_PATH, force_interactive=True)
        manager.guided_setup(edit_server='cpu_221')
    # 校验配置内容
    actual = load_yaml(TEST_CONFIG_PATH)
    expected = load_yaml(EXPECTED_CONFIG_PATH)
    assert actual == expected, f"配置内容不一致\n实际: {actual}\n预期: {expected}"
    # 测试后清理
    if os.path.exists(TEST_CONFIG_PATH):
        os.remove(TEST_CONFIG_PATH)
