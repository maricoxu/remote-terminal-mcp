# -*- coding: utf-8 -*-
"""
自动化回归测试：测试 create_server_config 工具的交互式新增服务器配置能力
场景：用户输入『我要新增服务器配置』，程序应唤起交互界面，自动化输入各项参数，最终检查配置文件内容
"""
import os
import sys
import yaml
import tempfile
import shutil
import pytest
from unittest.mock import patch

# 修正 sys.path，采用绝对包导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config_manager.main import EnhancedConfigManager

print('>>> EnhancedConfigManager loaded from:', EnhancedConfigManager)

TEST_CONFIG_PATH = os.path.join(tempfile.gettempdir(), "test_config_create_server.yaml")
EXPECTED_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "expected_test_create_server_config.yaml")

# 自动化交互输入序列（根据实际交互流程补充/调整）
MOCK_INPUTS = [
    "test_server_001",           # 服务器名称
    "testuser@test-host-001",    # 服务器地址 user@host
    "22",                        # 端口（明确输入22，避免空字符串）
    "2",                         # 是否启用docker（1=启用，2=不使用）
    "2",                         # 是否启用自动同步（1=启用，2=不使用）
    "", "", "", "", "",         # 预留给后续所有可选/确认输入
]

def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def test_interactive_create_server_config():
    # 测试前清理
    if os.path.exists(TEST_CONFIG_PATH):
        os.remove(TEST_CONFIG_PATH)
    # patch smart_input，严格按guided_setup字段顺序消费
    # 普通场景字段顺序：服务器名称, 主机名, 用户名, 端口, docker_enabled, auto_sync_enabled
    PATCH_INPUTS = [
        "test_server_001",        # 服务器名称
        "test-host-001",          # 主机名
        "testuser",               # 用户名
        "22",                     # 端口
        "2",                      # docker_enabled
        "2",                      # auto_sync_enabled
    ]
    with patch.object(EnhancedConfigManager, 'smart_input', side_effect=PATCH_INPUTS):
        manager = EnhancedConfigManager(config_path=TEST_CONFIG_PATH, force_interactive=True)
        manager.guided_setup()
    # 校验配置内容
    actual = load_yaml(TEST_CONFIG_PATH)
    expected = load_yaml(EXPECTED_CONFIG_PATH)
    assert actual == expected, f"配置内容不一致\n实际: {actual}\n预期: {expected}"
    # 测试后清理
    if os.path.exists(TEST_CONFIG_PATH):
        os.remove(TEST_CONFIG_PATH)
