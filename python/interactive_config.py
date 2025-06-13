#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
交互式配置管理器 - 让用户轻松创建和管理服务器配置

主要功能：
1. 交互式创建新服务器配置
2. 配置模板和快速复制
3. 配置验证和测试
4. 可视化配置管理
"""

import os
import sys
import yaml
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import subprocess
import re
from dataclasses import dataclass, asdict
from datetime import datetime
import getpass


def print_banner(text: str, char: str = "=", width: int = 60):
    """打印横幅"""
    print()
    print(char * width)
    print(f"  {text}")
    print(char * width)
    print()


def print_step(step: int, total: int, description: str):
    """打印步骤信息"""
    print(f"📋 步骤 {step}/{total}: {description}")
    print()


def get_user_input(prompt: str, default: str = "", required: bool = True, 
                   validation_func=None, help_text: str = "") -> str:
    """获取用户输入，支持默认值和验证"""
    while True:
        if default:
            display_prompt = f"{prompt} [{default}]: "
        else:
            display_prompt = f"{prompt}: "
        
        if help_text:
            print(f"💡 {help_text}")
        
        user_input = input(display_prompt).strip()
        
        # 使用默认值
        if not user_input and default:
            user_input = default
        
        # 检查必填项
        if required and not user_input:
            print("❌ 此项为必填项，请输入有效值")
            continue
        
        # 自定义验证
        if validation_func and user_input:
            is_valid, error_msg = validation_func(user_input)
            if not is_valid:
                print(f"❌ {error_msg}")
                continue
        
        return user_input


def validate_hostname(hostname: str) -> Tuple[bool, str]:
    """验证主机名格式"""
    if not hostname:
        return True, ""
    
    # 基本格式检查
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$'
    if not re.match(pattern, hostname):
        return False, "主机名格式不正确"
    
    return True, ""


def validate_port(port_str: str) -> Tuple[bool, str]:
    """验证端口号"""
    if not port_str:
        return True, ""
    
    try:
        port = int(port_str)
        if 1 <= port <= 65535:
            return True, ""
        else:
            return False, "端口号必须在1-65535之间"
    except ValueError:
        return False, "端口号必须是数字"


@dataclass
class ServerConfig:
    """服务器配置数据类"""
    name: str
    host: str
    username: str
    port: int = 22
    connection_type: str = "ssh"  # ssh, relay, jump
    description: str = ""
    
    # Relay特定配置
    relay_target_host: str = ""
    
    # 跳板机配置
    jump_host: str = ""
    
    # Docker配置
    docker_enabled: bool = False
    docker_container: str = ""
    docker_image: str = ""
    
    # 环境配置
    bos_bucket: str = ""
    tmux_session_prefix: str = ""
    
    def to_yaml_dict(self) -> Dict[str, Any]:
        """转换为YAML配置格式"""
        config = {
            "host": self.host,
            "username": self.username,
            "port": self.port
        }
        
        if self.description:
            config["description"] = self.description
        
        # 连接配置
        if self.connection_type == "relay":
            config["specs"] = {
                "connection": {
                    "tool": "relay",
                    "target": {
                        "host": self.relay_target_host
                    }
                }
            }
        elif self.connection_type == "jump":
            config["specs"] = {
                "connection": {
                    "tool": "jump",
                    "jump_host": self.jump_host,
                    "target": {
                        "host": self.relay_target_host
                    }
                }
            }
        
        # Docker配置
        if self.docker_enabled:
            docker_config = {}
            if self.docker_container:
                docker_config["container"] = self.docker_container
            if self.docker_image:
                docker_config["image"] = self.docker_image
            
            if docker_config:
                if "specs" not in config:
                    config["specs"] = {}
                config["specs"]["docker"] = docker_config
        
        # 环境配置
        if self.bos_bucket or self.tmux_session_prefix:
            env_config = {}
            if self.bos_bucket:
                env_config["BOS_BUCKET"] = self.bos_bucket
            if self.tmux_session_prefix:
                env_config["TMUX_SESSION_PREFIX"] = self.tmux_session_prefix
            
            if env_config:
                if "specs" not in config:
                    config["specs"] = {}
                config["specs"]["environment"] = env_config
        
        return config


class InteractiveConfigManager:
    """交互式配置管理器"""
    
    def __init__(self, config_path: str = None):
        """初始化配置管理器"""
        if config_path:
            self.config_path = Path(config_path)
        else:
            # 使用原来的配置路径
            home = Path.home()
            self.config_path = home / ".remote-terminal-mcp" / "config.yaml"
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载现有配置
        self.servers = self._load_existing_config()
    
    def _load_existing_config(self) -> Dict[str, Any]:
        """加载现有配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"⚠️ 加载配置文件失败: {e}")
                return {}
        return {}
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.servers, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            print(f"✅ 配置已保存到: {self.config_path}")
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def show_main_menu(self):
        """显示主菜单"""
        while True:
            print_banner("🚀 Remote Terminal 交互式配置管理器")
            
            print("请选择操作:")
            print("1. 📝 创建新服务器配置")
            print("2. 📋 查看现有配置")
            print("3. ✏️  编辑服务器配置")
            print("4. 🗑️  删除服务器配置")
            print("5. 🧪 测试服务器连接")
            print("6. 📤 导出配置")
            print("7. 📥 导入配置")
            print("8. 🚪 退出")
            print()
            
            choice = input("请输入选项 (1-8): ").strip()
            
            if choice == "1":
                self.create_new_server()
            elif choice == "2":
                self.list_servers()
            elif choice == "3":
                self.edit_server()
            elif choice == "4":
                self.delete_server()
            elif choice == "5":
                self.test_connection()
            elif choice == "6":
                self.export_config()
            elif choice == "7":
                self.import_config()
            elif choice == "8":
                print("👋 再见！")
                break
            else:
                print("❌ 无效选项，请重新选择")
            
            input("\n按回车键继续...")
    
    def create_new_server(self):
        """创建新服务器配置"""
        print_banner("📝 创建新服务器配置")
        
        # 步骤1: 基本信息
        print_step(1, 6, "基本服务器信息")
        
        name = get_user_input(
            "服务器名称 (用于识别，如: cpu-221, gpu-01)",
            help_text="这个名称将用于连接命令，建议使用简短易记的名称"
        )
        
        if name in self.servers:
            overwrite = input(f"⚠️ 服务器 '{name}' 已存在，是否覆盖? (y/N): ").strip().lower()
            if overwrite != 'y':
                print("❌ 操作已取消")
                return
        
        host = get_user_input(
            "服务器地址 (IP或域名)",
            validation_func=validate_hostname,
            help_text="例如: 192.168.1.100 或 server.example.com"
        )
        
        username = get_user_input(
            "用户名",
            default=getpass.getuser(),
            help_text="登录服务器使用的用户名"
        )
        
        port_str = get_user_input(
            "SSH端口",
            default="22",
            required=False,
            validation_func=validate_port
        )
        port = int(port_str) if port_str else 22
        
        description = get_user_input(
            "服务器描述 (可选)",
            required=False,
            help_text="例如: 开发服务器、GPU训练机器等"
        )
        
        # 步骤2: 连接方式
        print_step(2, 6, "连接方式配置")
        print("选择连接方式:")
        print("1. 🔗 直接SSH连接")
        print("2. 🌉 通过内网跳板机连接 (relay-cli)")
        print("3. 🔀 通过二级跳板机连接")
        
        conn_choice = get_user_input("请选择 (1-3)", default="1")
        
        connection_type = "ssh"
        relay_target_host = ""
        jump_host = ""
        
        if conn_choice == "2":
            connection_type = "relay"
            relay_target_host = get_user_input(
                "目标服务器地址 (跳板机后的实际服务器)",
                validation_func=validate_hostname,
                help_text="通过跳板机连接的最终目标服务器地址"
            )
        elif conn_choice == "3":
            connection_type = "jump"
            jump_host = get_user_input(
                "跳板机地址",
                validation_func=validate_hostname,
                help_text="第一级跳板机的地址"
            )
            relay_target_host = get_user_input(
                "目标服务器地址 (通过跳板机后的实际服务器)",
                validation_func=validate_hostname,
                help_text="通过跳板机连接的最终目标服务器地址"
            )
        
        # 步骤3: Docker配置
        print_step(3, 6, "Docker环境配置")
        
        docker_enabled = input("是否使用Docker容器? (y/N): ").strip().lower() == 'y'
        docker_container = ""
        docker_image = ""
        
        if docker_enabled:
            docker_container = get_user_input(
                "Docker容器名称",
                default="xyh_pytorch",
                help_text="连接时要进入的Docker容器名称"
            )
            
            docker_image = get_user_input(
                "Docker镜像 (可选)",
                required=False,
                help_text="如果容器不存在，使用此镜像创建。留空则不自动创建"
            )
        
        # 步骤4: 环境变量
        print_step(4, 6, "环境变量配置")
        
        bos_bucket = get_user_input(
            "BOS存储桶路径 (可选)",
            default=f"bos:/klx-pytorch-work-bd-bj/{getpass.getuser()}/template",
            required=False,
            help_text="云存储桶，用于文件同步"
        )
        
        tmux_session_prefix = get_user_input(
            "Tmux会话前缀 (可选)",
            default=name.replace('-', '').replace('_', '') + "_dev",
            required=False,
            help_text="Tmux会话名称前缀，用于区分不同服务器的会话"
        )
        
        # 步骤5: 配置预览
        print_step(5, 6, "配置预览")
        
        server_config = ServerConfig(
            name=name,
            host=host,
            username=username,
            port=port,
            connection_type=connection_type,
            description=description,
            relay_target_host=relay_target_host,
            jump_host=jump_host,
            docker_enabled=docker_enabled,
            docker_container=docker_container,
            docker_image=docker_image,
            bos_bucket=bos_bucket,
            tmux_session_prefix=tmux_session_prefix
        )
        
        self._preview_config(server_config)
        
        # 步骤6: 确认保存
        print_step(6, 6, "确认保存")
        
        confirm = input("确认保存此配置? (Y/n): ").strip().lower()
        if confirm in ['', 'y', 'yes']:
            self.servers[name] = server_config.to_yaml_dict()
            self._save_config()
            print(f"✅ 服务器 '{name}' 配置已创建成功！")
            
            # 询问是否立即测试连接
            test_now = input("是否立即测试连接? (y/N): ").strip().lower()
            if test_now == 'y':
                self._test_server_connection(name)
        else:
            print("❌ 配置未保存")
    
    def _preview_config(self, config: ServerConfig):
        """预览配置"""
        print("📋 配置预览:")
        print("-" * 40)
        print(f"服务器名称: {config.name}")
        print(f"服务器地址: {config.host}:{config.port}")
        print(f"用户名: {config.username}")
        print(f"连接方式: {config.connection_type}")
        
        if config.description:
            print(f"描述: {config.description}")
        
        if config.connection_type == "relay":
            print(f"目标服务器: {config.relay_target_host}")
        elif config.connection_type == "jump":
            print(f"跳板机: {config.jump_host}")
            print(f"目标服务器: {config.relay_target_host}")
        
        if config.docker_enabled:
            print(f"Docker容器: {config.docker_container}")
            if config.docker_image:
                print(f"Docker镜像: {config.docker_image}")
        
        if config.bos_bucket:
            print(f"BOS存储桶: {config.bos_bucket}")
        
        if config.tmux_session_prefix:
            print(f"Tmux会话: {config.tmux_session_prefix}")
        
        print("-" * 40)
        print()
    
    def list_servers(self):
        """列出所有服务器配置"""
        print_banner("📋 现有服务器配置")
        
        if not self.servers:
            print("📭 暂无服务器配置")
            return
        
        print(f"配置文件位置: {self.config_path}")
        print()
        
        for i, (name, config) in enumerate(self.servers.items(), 1):
            print(f"{i}. 🖥️  {name}")
            print(f"   地址: {config.get('username', 'unknown')}@{config.get('host', 'unknown')}:{config.get('port', 22)}")
            
            description = config.get('description', '')
            if description:
                print(f"   描述: {description}")
            
            # 连接方式
            specs = config.get('specs', {})
            connection = specs.get('connection', {})
            if connection.get('tool') == 'relay':
                target_host = connection.get('target', {}).get('host', '')
                print(f"   连接: Relay -> {target_host}")
            elif connection.get('tool') == 'jump':
                jump_host = connection.get('jump_host', '')
                target_host = connection.get('target', {}).get('host', '')
                print(f"   连接: Jump ({jump_host}) -> {target_host}")
            else:
                print(f"   连接: 直接SSH")
            
            # Docker信息
            docker = specs.get('docker', {})
            if docker:
                container = docker.get('container', '')
                print(f"   Docker: {container}")
            
            print()
    
    def edit_server(self):
        """编辑服务器配置"""
        print_banner("✏️ 编辑服务器配置")
        
        if not self.servers:
            print("📭 暂无服务器配置")
            return
        
        # 显示服务器列表
        server_names = list(self.servers.keys())
        for i, name in enumerate(server_names, 1):
            print(f"{i}. {name}")
        
        print()
        choice = get_user_input("请选择要编辑的服务器 (输入编号或名称)")
        
        # 解析选择
        server_name = None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(server_names):
                server_name = server_names[idx]
        else:
            if choice in self.servers:
                server_name = choice
        
        if not server_name:
            print("❌ 无效的服务器选择")
            return
        
        print(f"📝 编辑服务器: {server_name}")
        print("💡 直接按回车保持当前值不变")
        print()
        
        # 获取当前配置
        current = self.servers[server_name]
        specs = current.get('specs', {})
        
        # 编辑基本信息
        new_host = get_user_input("服务器地址", default=current.get('host', ''), required=False)
        new_username = get_user_input("用户名", default=current.get('username', ''), required=False)
        new_port = get_user_input("端口", default=str(current.get('port', 22)), required=False)
        new_description = get_user_input("描述", default=current.get('description', ''), required=False)
        
        # 更新配置
        if new_host:
            current['host'] = new_host
        if new_username:
            current['username'] = new_username
        if new_port:
            current['port'] = int(new_port)
        if new_description:
            current['description'] = new_description
        
        self._save_config()
        print(f"✅ 服务器 '{server_name}' 配置已更新")
    
    def delete_server(self):
        """删除服务器配置"""
        print_banner("🗑️ 删除服务器配置")
        
        if not self.servers:
            print("📭 暂无服务器配置")
            return
        
        # 显示服务器列表
        server_names = list(self.servers.keys())
        for i, name in enumerate(server_names, 1):
            print(f"{i}. {name}")
        
        print()
        choice = get_user_input("请选择要删除的服务器 (输入编号或名称)")
        
        # 解析选择
        server_name = None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(server_names):
                server_name = server_names[idx]
        else:
            if choice in self.servers:
                server_name = choice
        
        if not server_name:
            print("❌ 无效的服务器选择")
            return
        
        # 确认删除
        confirm = input(f"⚠️ 确认删除服务器 '{server_name}' 的配置? (y/N): ").strip().lower()
        if confirm == 'y':
            del self.servers[server_name]
            self._save_config()
            print(f"✅ 服务器 '{server_name}' 配置已删除")
        else:
            print("❌ 删除操作已取消")
    
    def test_connection(self):
        """测试服务器连接"""
        print_banner("🧪 测试服务器连接")
        
        if not self.servers:
            print("📭 暂无服务器配置")
            return
        
        # 显示服务器列表
        server_names = list(self.servers.keys())
        for i, name in enumerate(server_names, 1):
            print(f"{i}. {name}")
        
        print()
        choice = get_user_input("请选择要测试的服务器 (输入编号或名称)")
        
        # 解析选择
        server_name = None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(server_names):
                server_name = server_names[idx]
        else:
            if choice in self.servers:
                server_name = choice
        
        if not server_name:
            print("❌ 无效的服务器选择")
            return
        
        self._test_server_connection(server_name)
    
    def _test_server_connection(self, server_name: str):
        """测试指定服务器的连接"""
        print(f"🧪 测试连接: {server_name}")
        print("⏳ 正在测试连接...")
        
        try:
            # 这里可以集成实际的连接测试逻辑
            # 暂时使用简单的ping测试
            config = self.servers[server_name]
            host = config.get('host', '')
            
            if host:
                result = subprocess.run(['ping', '-c', '1', '-W', '3000', host], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ 服务器 {host} 网络连通性正常")
                else:
                    print(f"❌ 服务器 {host} 网络不通")
            
            print("💡 完整连接测试需要使用 remote-terminal 工具")
            
        except Exception as e:
            print(f"❌ 连接测试失败: {e}")
    
    def export_config(self):
        """导出配置"""
        print_banner("📤 导出配置")
        
        export_path = get_user_input(
            "导出文件路径",
            default=f"remote-terminal-config-{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml",
            help_text="配置将导出为YAML文件"
        )
        
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.servers, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            print(f"✅ 配置已导出到: {export_path}")
        except Exception as e:
            print(f"❌ 导出失败: {e}")
    
    def import_config(self):
        """导入配置"""
        print_banner("📥 导入配置")
        
        import_path = get_user_input("导入文件路径")
        
        if not os.path.exists(import_path):
            print("❌ 文件不存在")
            return
        
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_servers = yaml.safe_load(f) or {}
            
            if not isinstance(imported_servers, dict):
                print("❌ 配置文件格式不正确")
                return
            
            # 显示将要导入的服务器
            print("📋 将要导入的服务器:")
            for name in imported_servers.keys():
                print(f"  - {name}")
            
            print()
            merge_mode = input("选择导入模式:\n1. 合并 (保留现有配置)\n2. 覆盖 (替换所有配置)\n请选择 (1-2): ").strip()
            
            if merge_mode == "2":
                self.servers = imported_servers
            else:
                # 合并模式
                conflicts = []
                for name in imported_servers.keys():
                    if name in self.servers:
                        conflicts.append(name)
                
                if conflicts:
                    print(f"⚠️ 发现冲突的服务器配置: {', '.join(conflicts)}")
                    overwrite = input("是否覆盖冲突的配置? (y/N): ").strip().lower()
                    if overwrite != 'y':
                        # 只导入不冲突的配置
                        for name, config in imported_servers.items():
                            if name not in self.servers:
                                self.servers[name] = config
                    else:
                        self.servers.update(imported_servers)
                else:
                    self.servers.update(imported_servers)
            
            self._save_config()
            print("✅ 配置导入成功")
            
        except Exception as e:
            print(f"❌ 导入失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Remote Terminal 交互式配置管理器")
    parser.add_argument("--config", "-c", help="配置文件路径")
    parser.add_argument("--create", help="快速创建服务器配置")
    
    args = parser.parse_args()
    
    manager = InteractiveConfigManager(args.config)
    
    if args.create:
        # 快速创建模式
        print(f"🚀 快速创建服务器配置: {args.create}")
        # 这里可以实现快速创建逻辑
    else:
        # 交互式菜单模式
        manager.show_main_menu()


if __name__ == "__main__":
    main()