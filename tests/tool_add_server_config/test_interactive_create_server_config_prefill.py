# -*- coding: utf-8 -*-
"""
自动化回归测试：测试 create_server_config 工具的参数预填充能力
场景：用户输入『我要新增一个服务器hg225，它的hostname是192.168.1.225，用户名admin』，程序应自动预填参数，唤起交互界面，自动化输入其余参数，最终检查配置文件内容
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

TEST_CONFIG_PATH = os.path.join(tempfile.gettempdir(), "test_config_create_server_prefill.yaml")
EXPECTED_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "expected_test_create_server_config_prefill.yaml")

MOCK_INPUTS = [
    "",  # 服务器名称（已预填）
    "",  # 服务器地址（已预填）
    "22",  # 端口（明确输入22，避免空字符串）
    "2", # 是否启用docker
    "2", # 是否启用自动同步
    "", "", "", "", "",  # 预留给后续所有可选/确认输入
]

def test_interactive_create_server_config_prefill():
    # 测试前清理
    if os.path.exists(TEST_CONFIG_PATH):
        os.remove(TEST_CONFIG_PATH)
    # 预填参数
    prefill = {
        'name': 'hg225',
        'host': '192.168.1.225',
        'username': 'admin',
    }
    with patch("builtins.input", side_effect=MOCK_INPUTS):
        manager = EnhancedConfigManager(config_path=TEST_CONFIG_PATH, force_interactive=True)
        with patch.object(manager.ia, 'smart_input', side_effect=lambda prompt, **kwargs: "22" if "端口" in prompt else (MOCK_INPUTS.pop(0) if MOCK_INPUTS else "test")):
            manager.guided_setup(prefill=prefill)
    # 校验配置内容
    actual = load_yaml(TEST_CONFIG_PATH)
    expected = load_yaml(EXPECTED_CONFIG_PATH)
    assert actual == expected, f"配置内容不一致\n实际: {actual}\n预期: {expected}"
    # 测试后清理
    if os.path.exists(TEST_CONFIG_PATH):
        os.remove(TEST_CONFIG_PATH)
