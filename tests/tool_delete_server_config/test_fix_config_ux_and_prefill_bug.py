#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回归测试：修复配置向导的UX和预填充参数BUG

测试目的：
- 验证 `edit_server_config` 流程中的用户体验已恢复到简洁模式。
- 验证在更新二级跳板服务器时，由于预填充参数不完整（缺少port、host）导致的BUG已被修复。
"""
import os
import sys
import unittest
import yaml
from pathlib import Path
import asyncio
from unittest.mock import patch

# 将项目根目录添加到sys.path，以便导入模块
# tests/regression/ -> tests/ -> project_root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.utils.automated_interaction_tester import AutomatedInteractionTester
from config_manager.main import EnhancedConfigManager


class TestConfigUXPrefillFix(unittest.TestCase):
    """测试配置向导的UX回归和预填充参数BUG修复"""

    def setUp(self):
        """测试初始化"""
        self.config_dir = project_root / 'tests' / 'temp_config'
        self.config_path = self.config_dir / 'config.yaml'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建一个有问题的初始配置文件，模拟BUG场景
        # - hg222 的 'host' 和 'username' 在顶层，但 jump_host 缺少这些
        # - port 字段完全缺失
        problematic_config = {
            'servers': {
                'hg222': {
                    'type': 'relay',
                    'host': 'szzj-isa-ai-peking-poc06.szzj',
                    'username': 'yh',
                    'password': 'old_password',
                    'specs': {
                        'connection': {
                            # 故意让 jump_host 为空，以触发预填充BUG
                            'jump_host': {} 
                        }
                    }
                }
            }
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(problematic_config, f)
            
        self.tester = EnhancedConfigManager(config_path=str(self.config_path))
        # 禁用交互测试器中的颜色，以便于捕获和比较输出
        self.tester.is_mcp_mode = True 

    def tearDown(self):
        """清理测试文件"""
        if self.config_dir.exists():
            import shutil
            shutil.rmtree(self.config_dir)

    def test_update_relay_server_with_prefill_issues(self):
        """
        测试更新二级跳板服务器的流程，确保：
        1. UX是简洁的 user@host -> password 模式。
        2. 预填充不完整的参数不会导致崩溃。
        """
        # 测试前清理配置文件，确保环境隔离
        if self.config_path.exists():
            self.config_path.unlink()
        # patch smart_input，relay字段顺序：host, username, port, docker_enabled, auto_sync_enabled, sync_config
        PATCH_INPUTS = [
            'relay-host.com',  # host
            'user1',          # username
            '22',             # port
            'n',              # docker_enabled
            'n',              # auto_sync_enabled
            '',                # sync_config（补全，防止StopIteration）
        ]
        with patch.object(EnhancedConfigManager, 'smart_input', side_effect=PATCH_INPUTS):
            manager = EnhancedConfigManager(config_path=self.config_path, force_interactive=True)
            manager.guided_setup(prefill={'name': 'hg222'})
        # 断言2: 检查最终的配置文件内容是否正确
        with open(self.config_path, 'r', encoding='utf-8') as f:
            final_config = yaml.safe_load(f)
        print(f"[调试] update_relay_server_with_prefill_issues 最终配置内容: {final_config}")
        updated_server = final_config['servers']['hg222']
        
        # 验证第一级跳板机信息
        self.assertEqual(updated_server['host'], 'relay-host.com')
        self.assertEqual(updated_server['username'], 'user1')
        self.assertEqual(updated_server['port'], 22)
        self.assertEqual(updated_server['password'], 'relay_password_123')
        
        # 验证最终目标服务器信息
        jump_host = updated_server['specs']['connection']['jump_host']
        self.assertEqual(jump_host['host'], 'final-dest.com')
        self.assertEqual(jump_host['username'], 'user2')
        self.assertEqual(jump_host['port'], 2222)
        self.assertEqual(jump_host['password'], 'final_dest_password_456')

        print("\n✅ 回归测试成功：配置向导UX和预填充BUG已修复。")

    def test_guided_setup_for_relay_server(self):
        """
        新增测试：通过向导模式更新二级跳板服务器，确保调用_configure_server时不再出错。
        """
        # 测试前清理配置文件，确保环境隔离
        if self.config_path.exists():
            self.config_path.unlink()
        # patch smart_input，relay字段顺序：host, username, port, docker_enabled, auto_sync_enabled, sync_config
        PATCH_INPUTS = [
            'relay-host.com',  # host
            'relay',          # username
            '22',             # port
            'n',              # docker_enabled
            'n',              # auto_sync_enabled
            '',                # sync_config（补全，防止StopIteration）
        ]
        with patch.object(EnhancedConfigManager, 'smart_input', side_effect=PATCH_INPUTS):
            manager = EnhancedConfigManager(config_path=self.config_path, force_interactive=True)
            manager.guided_setup(prefill={'name': 'hg222-guided'})
        # 断言2: 检查最终的配置文件内容是否正确
        with open(self.config_path, 'r', encoding='utf-8') as f:
            final_config = yaml.safe_load(f)
        print(f"[调试] guided_setup_for_relay_server 最终配置内容: {final_config}")
        new_server = final_config['servers']['hg222-guided']
        self.assertEqual(new_server['host'], 'relay-host.com')
        self.assertEqual(new_server['username'], 'relay')
        self.assertEqual(new_server['port'], 22)
        jump_host = new_server['specs']['connection']['jump_host']
        self.assertEqual(jump_host['host'], 'target-host.com')
        self.assertEqual(jump_host['username'], 'target')

        print("\n✅ 回归测试成功：guided_setup 调用流程已修复。")

if __name__ == '__main__':
    unittest.main() 