#!/usr/bin/env python3
"""
Enhanced Configuration Manager for Remote Terminal MCP
支持4种配置方式的综合管理工具
基于CONFIG_UX_DESIGN.md的最佳实践设计
"""

import os
import sys
import yaml
import json
import subprocess
import tempfile
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from docker_config_manager import DockerConfigManager, DockerEnvironmentConfig

# 添加颜色支持
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    # 如果没有colorama，使用简单的颜色代码
    class Fore:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        MAGENTA = '\033[95m'
        CYAN = '\033[96m'
        WHITE = '\033[97m'
        RESET = '\033[0m'
    
    class Style:
        BRIGHT = '\033[1m'
        RESET_ALL = '\033[0m'
    
    HAS_COLOR = True

class ConfigError:
    """错误类型定义"""
    WARNING = "⚠️"
    ERROR = "❌"
    INFO = "ℹ️"
    SUCCESS = "✅"

class EnhancedConfigManager:
    def __init__(self, config_path: str = None):
        if config_path is None:
            # 使用用户家目录下的.remote-terminal-mcp文件夹
            self.config_dir = Path.home() / ".remote-terminal-mcp"
            self.config_path = self.config_dir / "config.yaml"
        else:
            self.config_path = Path(config_path)
            self.config_dir = self.config_path.parent
        self.templates_dir = self.config_dir / "templates"
        
        # 初始化Docker配置管理器
        self.docker_manager = DockerConfigManager(str(self.config_dir))
        
        self.ensure_directories()
        
    def colored_print(self, text: str, color=Fore.WHITE, style=""):
        """彩色打印函数"""
        if HAS_COLOR:
            print(f"{style}{color}{text}{Style.RESET_ALL}")
        else:
            print(text)
    
    def show_progress(self, current_step: int, total_steps: int, step_name: str):
        """显示进度指示器"""
        progress_bar = "█" * current_step + "░" * (total_steps - current_step)
        self.colored_print(f"\n📊 进度: [{progress_bar}] {current_step}/{total_steps}", Fore.CYAN)
        self.colored_print(f"当前步骤: {step_name}", Fore.YELLOW)
    
    def smart_input(self, prompt: str, validator=None, suggestions=None, default="", show_suggestions=True):
        """智能输入函数，支持验证和建议"""
        if suggestions and show_suggestions:
            self.colored_print(f"💡 建议: {', '.join(suggestions)}", Fore.CYAN)
        
        if default:
            prompt_text = f"{prompt} [{default}]: "
        else:
            prompt_text = f"{prompt}: "
        
        while True:
            try:
                value = input(prompt_text).strip()
                if not value and default:
                    value = default
                
                if validator:
                    if validator(value):
                        return value
                    else:
                        self.colored_print(f"{ConfigError.ERROR} 输入格式不正确，请重试", Fore.RED)
                        continue
                else:
                    return value
            except KeyboardInterrupt:
                self.colored_print(f"\n{ConfigError.INFO} 操作已取消", Fore.YELLOW)
                return None
    
    def parse_user_host(self, user_host_input: str) -> tuple:
        """解析 user@host 格式的输入"""
        if '@' in user_host_input:
            parts = user_host_input.split('@', 1)
            if len(parts) == 2:
                user, host = parts
                if self.validate_username(user) and self.validate_hostname(host):
                    return user, host
        return None, None
    
    def _configure_server(self, server_type: str, ask_for_name: bool = True) -> dict:
        """配置服务器信息的辅助方法"""
        self.colored_print(f"\n📝 配置{server_type}信息", Fore.CYAN)
        
        # 服务器名称 (可选)
        server_name = None
        if ask_for_name:
            server_name = self.smart_input(f"🏷️ {server_type}名称", 
                                         validator=lambda x: bool(x and len(x) > 0),
                                         show_suggestions=False)
            if not server_name:
                return None
        
        # 支持user@host格式
        user_host_input = self.smart_input("👤 用户名@服务器地址 (或只输入服务器地址)", 
                                         show_suggestions=False)
        if not user_host_input:
            return None
        
        # 尝试解析user@host格式
        username, server_host = self.parse_user_host(user_host_input)
        
        if username and server_host:
            # 成功解析user@host格式
            self.colored_print(f"✅ 解析成功: {username}@{server_host}", Fore.GREEN)
        elif self.validate_hostname(user_host_input):
            # 只输入了服务器地址
            server_host = user_host_input
            self.colored_print(f"📍 服务器地址: {server_host}", Fore.CYAN)
            
            current_user = os.getenv('USER', 'user')
            username = self.smart_input(f"👤 用户名", 
                                      validator=self.validate_username,
                                      default=current_user,
                                      show_suggestions=False)
            if not username:
                return None
        else:
            self.colored_print("❌ 输入格式不正确", Fore.RED)
            return None
        
        # SSH端口（如果需要）
        port = None
        if server_type == "目标服务器":
            port = self.smart_input("🔌 SSH端口", 
                                   validator=self.validate_port,
                                   default="22",
                                   show_suggestions=False)
        
        # 密码配置
        password = None
        self.colored_print(f"\n🔐 {server_type}认证配置", Fore.YELLOW)
        password_input = self.smart_input("🔑 登录密码 (直接回车表示使用SSH密钥认证)", 
                                        default="",
                                        show_suggestions=False)
        if password_input.strip():
            password = password_input.strip()
            self.colored_print("✅ 已配置密码认证", Fore.GREEN)
        else:
            self.colored_print("✅ 将使用SSH密钥认证", Fore.GREEN)
        
        return {
            "name": server_name,
            "host": server_host,
            "user": username,
            "port": port,
            "password": password
        }
    
    def validate_hostname(self, hostname: str) -> bool:
        """验证主机名格式"""
        if not hostname:
            return False
        # 简单的主机名或IP验证
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$'
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        return bool(re.match(hostname_pattern, hostname) or re.match(ip_pattern, hostname))
    
    def validate_port(self, port_str: str) -> bool:
        """验证端口号"""
        try:
            port = int(port_str)
            return 1 <= port <= 65535
        except ValueError:
            return False
    
    def validate_username(self, username: str) -> bool:
        """验证用户名格式"""
        if not username:
            return False
        # 基本的用户名验证
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', username))

    def ensure_directories(self):
        """确保必要的目录存在"""
        self.config_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        self.create_default_templates()
    
    def create_default_templates(self):
        """创建默认配置模板"""
        templates = {
            "ssh_server.yaml": {
                "servers": {
                    "example-ssh": {
                        "host": "your-server.com",
                        "user": "your-username",
                        "port": 22,
                        "type": "ssh",
                        "description": "Standard SSH server"
                    }
                }
            },
            "relay_server.yaml": {
                "servers": {
                    "example-relay": {
                        "host": "target-server.internal",
                        "user": "your-username", 
                        "type": "relay",
                        "relay_command": "relay-cli -s target-server.internal",
                        "description": "Server via relay-cli"
                    }
                }
            },
            "docker_server.yaml": {
                "servers": {
                    "example-docker": {
                        "host": "docker-host.com",
                        "user": "your-username",
                        "type": "docker",
                        "container_name": "dev_container",
                        "docker_image": "ubuntu:20.04",
                        "auto_create_container": True,
                        "tmux_session": "dev_session",
                        "description": "Docker development environment"
                    }
                }
            },
            "complex_server.yaml": {
                "servers": {
                    "example-complex": {
                        "host": "complex-server.com",
                        "user": "developer",
                        "port": 2222,
                        "type": "relay",
                        "relay_command": "relay-cli -s complex-server.com",
                        "container_name": "pytorch_env",
                        "docker_image": "pytorch/pytorch:latest",
                        "auto_create_container": True,
                        "tmux_session": "ml_work",
                        "environment": {
                            "CUDA_VISIBLE_DEVICES": "0,1",
                            "PYTHONPATH": "/workspace"
                        },
                        "post_connect_commands": [
                            "cd /workspace",
                            "source activate pytorch",
                            "echo 'Environment ready!'"
                        ],
                        "description": "Complex ML development environment"
                    }
                }
            }
        }
        
        for template_name, content in templates.items():
            template_path = self.templates_dir / template_name
            if not template_path.exists():
                with open(template_path, 'w', encoding='utf-8') as f:
                    yaml.dump(content, f, default_flow_style=False, allow_unicode=True)
    
    def main_menu(self):
        """主菜单 - 简化版"""
        self.colored_print("\n🚀 Remote Terminal Configuration Manager", Fore.CYAN, Style.BRIGHT)
        self.colored_print("=" * 50, Fore.CYAN)
        
        self.colored_print("\n📋 配置选项:", Fore.GREEN, Style.BRIGHT)
        self.colored_print("  1. 向导配置 (Guided Setup) - 推荐使用", Fore.GREEN)
        self.colored_print("  2. 手动配置 (Manual Setup) - 直接编辑配置文件", Fore.BLUE)
        self.colored_print("  3. 🐳 创建docker容器环境配置", Fore.CYAN)
        
        self.colored_print("\n⚙️ 管理功能:", Fore.MAGENTA, Style.BRIGHT)
        self.colored_print("  4. 管理现有配置", Fore.MAGENTA)
        self.colored_print("  5. 测试连接", Fore.MAGENTA)
        self.colored_print("  0. 退出", Fore.WHITE)
        
        self.colored_print("=" * 50, Fore.CYAN)
        
        while True:
            choice = self.smart_input("\n请选择操作", 
                                    validator=lambda x: x in ['0', '1', '2', '3', '4', '5'],
                                    show_suggestions=False)
            
            if choice is None:  # 用户取消
                return
            elif choice == "1":
                return self.guided_setup()
            elif choice == "2":
                return self.manual_setup()
            elif choice == "3":
                return self.docker_wizard_setup()
            elif choice == "4":
                return self.manage_existing()
            elif choice == "5":
                return self.test_connection()
            elif choice == "0":
                self.colored_print("👋 再见！", Fore.CYAN)
                return
            else:
                self.colored_print(f"{ConfigError.ERROR} 无效选择，请重新输入", Fore.RED)
    
    def quick_setup(self):
        """快速配置 - 改进版"""
        self.colored_print("\n⚡ 快速配置模式", Fore.YELLOW, Style.BRIGHT)
        self.colored_print("只需回答几个关键问题，5分钟完成配置", Fore.YELLOW)
        self.colored_print("-" * 40, Fore.YELLOW)
        
        self.show_progress(1, 5, "收集基本信息")
        
        # 基本信息
        server_name = self.smart_input("服务器名称", 
                                     validator=lambda x: bool(x and len(x) > 0),
                                     suggestions=["gpu-server-1", "dev-server", "ml-server"])
        if not server_name:
            return
            
        server_host = self.smart_input("服务器地址", 
                                     validator=self.validate_hostname,
                                     suggestions=["192.168.1.100", "server.example.com"])
        if not server_host:
            return
            
        username = self.smart_input("用户名", 
                                   validator=self.validate_username,
                                   suggestions=["ubuntu", "root", os.getenv('USER', 'user')])
        if not username:
            return
        
        self.show_progress(2, 5, "选择连接方式")
        
        # 连接方式
        self.colored_print("\n连接方式:", Fore.CYAN)
        self.colored_print("1. 直接SSH连接 (标准方式)", Fore.GREEN)
        self.colored_print("2. 通过relay-cli连接 (百度内网)", Fore.BLUE)
        
        connection_type = self.smart_input("选择连接方式", 
                                         validator=lambda x: x in ['1', '2'],
                                         suggestions=['1 (推荐)', '2 (内网)'])
        if not connection_type:
            return
        
        self.show_progress(3, 5, "Docker配置")
        
        # 是否使用Docker
        use_docker_input = self.smart_input("是否使用Docker容器", 
                                           validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
                                           suggestions=['y (推荐)', 'n'],
                                           default='n')
        if not use_docker_input:
            return
            
        use_docker = use_docker_input.lower() in ['y', 'yes']
        
        self.show_progress(4, 5, "生成配置")
        
        # 生成配置
        config = {"servers": {}}
        
        if connection_type == "2":
            # Relay连接
            token = self.smart_input("Relay token (可选，回车跳过)", default="")
            relay_cmd = f"relay-cli -t {token} -s {server_host}" if token else f"relay-cli -s {server_host}"
            
            config["servers"][server_name] = {
                "host": server_host,
                "user": username,
                "type": "relay",
                "relay_command": relay_cmd,
                "description": f"Quick setup: {server_name} via relay-cli"
            }
        else:
            # SSH连接
            port = self.smart_input("SSH端口", 
                                   validator=self.validate_port,
                                   default="22")
            if not port:
                return
                
            config["servers"][server_name] = {
                "host": server_host,
                "user": username,
                "port": int(port),
                "type": "ssh", 
                "description": f"Quick setup: {server_name} via SSH"
            }
        
        # Docker配置
        if use_docker:
            container_name = self.smart_input("Docker容器名称", 
                                            default="dev_env",
                                            suggestions=["dev_env", "pytorch_env", "ubuntu_dev"])
            if container_name:
                config["servers"][server_name].update({
                    "container_name": container_name,
                    "auto_create_container": True,
                    "tmux_session": f"{server_name}_session"
                })
        
        self.show_progress(5, 5, "保存配置")
        
        # 保存配置
        self.save_config(config)
        self.colored_print(f"\n{ConfigError.SUCCESS} 快速配置完成！", Fore.GREEN, Style.BRIGHT)
        self.colored_print(f"配置已保存到: {self.config_path}", Fore.GREEN)
        
    def guided_setup(self):
        """向导配置 - 重新设计的配置体验"""
        self.colored_print("\n🎯 向导配置模式", Fore.YELLOW, Style.BRIGHT)
        self.colored_print("📋 逐步引导，轻松完成服务器配置", Fore.YELLOW)
        self.colored_print("=" * 50, Fore.YELLOW)
        
        # 显示现有配置概览
        self.show_existing_configurations_overview()
        
        self.show_progress(1, 4, "选择连接方式")
        
        # 第1步：连接方式选择
        self.colored_print("\n🔗 第1步：连接方式选择", Fore.CYAN, Style.BRIGHT)
        self.colored_print("1. Relay跳板机连接 - 通过代理/跳板机连接 (推荐)", Fore.BLUE)
        self.colored_print("2. SSH直连 - 直接连接服务器", Fore.GREEN)
        
        connection_type = self.smart_input("选择连接方式", 
                                         validator=lambda x: x in ['1', '2'], 
                                         default='1',
                                         show_suggestions=False)
        if not connection_type:
            return
        
        self.show_progress(2, 4, "配置服务器信息")
        
        # 第2步：根据连接方式配置服务器
        if connection_type == "1":
            # Relay跳板机连接
            self.colored_print("\n🛰️ 第2步：配置Relay连接", Fore.CYAN, Style.BRIGHT)
            
            # 配置目标服务器
            target_server = self._configure_server("目标服务器")
            if not target_server:
                return
                
            # 询问是否需要二级跳板
            use_jump = self.smart_input("是否需要二级跳板机 (y/n)", 
                                      validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'] or x == '',
                                      default='n',
                                      show_suggestions=False)
            
            # 初始化配置
            config = {"servers": {target_server["name"]: {
                "host": target_server["host"],
                "username": target_server["user"],  # 修正字段名
                "port": int(target_server.get("port", 22)),
                "private_key_path": "~/.ssh/id_rsa",
                "type": "script_based",  # 统一使用script_based
                "connection_type": "relay",  # 添加连接类型标识
                "description": f"Relay连接: {target_server['name']}",
                "specs": {
                    "connection": {
                        "tool": "relay-cli",
                        "target": {"host": target_server["host"]}
                    }
                }
            }}}
            
            # 添加密码配置到主配置中
            if target_server.get("password"):
                config["servers"][target_server["name"]]["password"] = target_server["password"]
            
            # 如果需要二级跳板，配置中继服务器
            if use_jump and use_jump.lower() in ['y', 'yes']:
                self.colored_print("\n🏃 配置中继服务器 (第一级跳板机)", Fore.MAGENTA)
                self.colored_print("💡 连接流程: relay-cli → 中继服务器 → 目标服务器", Fore.YELLOW)
                
                relay_server = self._configure_server("中继服务器", ask_for_name=False)
                if relay_server:
                    # 在specs中配置中继服务器信息
                    config["servers"][target_server["name"]]["specs"]["connection"]["jump_host"] = {
                        "host": relay_server["host"],
                        "username": relay_server["user"]
                    }
                    # 如果中继服务器有密码，也要保存
                    if relay_server.get("password"):
                        config["servers"][target_server["name"]]["specs"]["connection"]["jump_host"]["password"] = relay_server["password"]
                    
        else:
            # SSH直连 - 只需配置目标服务器
            self.colored_print("\n🖥️ 第2步：配置目标服务器", Fore.CYAN, Style.BRIGHT)
            server_config = self._configure_server("目标服务器")
            if not server_config:
                return
                
            config = {"servers": {server_config["name"]: {
                "host": server_config["host"],
                "username": server_config["user"],  # 修正字段名
                "port": int(server_config.get("port", 22)),
                "private_key_path": "~/.ssh/id_rsa",
                "type": "script_based",  # 统一使用script_based
                "connection_type": "ssh",  # 添加连接类型标识
                "description": f"SSH直连: {server_config['name']}",
                "specs": {
                    "connection": {
                        "tool": "ssh",
                        "target": {"host": server_config["host"]}
                    }
                }
            }}}
            
            # 添加密码配置到SSH直连中
            if server_config.get("password"):
                config["servers"][server_config["name"]]["password"] = server_config["password"]

        
        self.show_progress(3, 4, "Docker配置")
        
        # 第3步：Docker配置 (智能选择)
        self.colored_print("\n🐳 第3步：Docker配置 (可选)", Fore.CYAN)
        use_docker_input = self.smart_input("是否使用Docker容器 (y/n)", 
                                           validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'] or x == '', 
                                           default='n',
                                           show_suggestions=False)
        if not use_docker_input:
            use_docker_input = 'n'
            
        # 获取主服务器名称（用于容器命名和tmux会话）
        main_server_name = list(config["servers"].keys())[0]
        main_server_user = config["servers"][main_server_name]["username"]
            
        if use_docker_input.lower() in ['y', 'yes']:
            # 检查现有Docker配置
            existing_docker_configs = self.get_existing_docker_configs()
            
            if existing_docker_configs:
                self.colored_print("\n🐳 发现现有Docker配置:", Fore.BLUE, Style.BRIGHT)
                docker_list = list(existing_docker_configs.items())
                for i, (config_name, config_info) in enumerate(docker_list, 1):
                    image = config_info.get('image', 'unknown')
                    container_name = config_info.get('container_name', config_name)
                    self.colored_print(f"  {i}. {container_name} - {image}", Fore.WHITE)
                
                self.colored_print("\n📋 Docker配置选项:", Fore.CYAN)
                self.colored_print("  1. 使用现有Docker配置", Fore.GREEN)
                self.colored_print("  2. 创建新的Docker配置", Fore.YELLOW)
                
                docker_choice = self.smart_input("选择Docker配置方式", 
                                                validator=lambda x: x in ['1', '2'],
                                                show_suggestions=False)
                
                if docker_choice == "1":
                    # 使用现有配置
                    if len(docker_list) == 1:
                        # 只有一个配置，直接使用
                        selected_config_name, selected_config = docker_list[0]
                        self.colored_print(f"✅ 已选择Docker配置: {selected_config['container_name']}", Fore.GREEN)
                    else:
                        # 多个配置，让用户选择
                        self.colored_print(f"\n📋 请选择要使用的Docker配置:", Fore.CYAN)
                        # 重新显示配置列表供选择
                        for i, (config_name, config_info) in enumerate(docker_list, 1):
                            image = config_info.get('image', 'unknown')
                            container_name = config_info.get('container_name', config_name)
                            self.colored_print(f"  {i}. {container_name} - {image}", Fore.WHITE)
                        
                        config_choice = self.smart_input(f"选择Docker配置 (1-{len(docker_list)})", 
                                                        validator=lambda x: x.isdigit() and 1 <= int(x) <= len(docker_list))
                        if not config_choice:
                            return
                        selected_config_name, selected_config = docker_list[int(config_choice) - 1]
                        self.colored_print(f"✅ 已选择Docker配置: {selected_config['container_name']}", Fore.GREEN)
                    
                    # 使用选中的Docker配置
                    if "specs" not in config["servers"][main_server_name]:
                        config["servers"][main_server_name]["specs"] = {}
                    config["servers"][main_server_name]["specs"]["docker"] = {
                        "container_name": selected_config['container_name'],
                        "image": selected_config['image'],
                        "auto_create": True,
                        "ports": selected_config.get('ports', []),
                        "volumes": selected_config.get('volumes', [])
                    }
                    
                elif docker_choice == "2":
                    # 创建新配置 - 跳转到Docker向导
                    self.colored_print("\n🚀 跳转到Docker配置向导...", Fore.CYAN)
                    docker_config_result = self.docker_wizard_setup(called_from_guided_setup=True)
                    
                    # Docker向导完成后，获取最新的Docker配置并应用到当前服务器
                    if docker_config_result:
                        updated_docker_configs = self.get_existing_docker_configs()
                        if updated_docker_configs:
                            # 获取最新创建的配置（假设是最后一个）
                            latest_config_name = list(updated_docker_configs.keys())[-1]
                            latest_config = updated_docker_configs[latest_config_name]
                            
                            if "specs" not in config["servers"][main_server_name]:
                                config["servers"][main_server_name]["specs"] = {}
                            config["servers"][main_server_name]["specs"]["docker"] = {
                                "container_name": latest_config['container_name'],
                                "image": latest_config['image'],
                                "auto_create": True,
                                "ports": latest_config.get('ports', []),
                                "volumes": latest_config.get('volumes', [])
                            }
                            self.colored_print(f"✅ 已应用新Docker配置: {latest_config['container_name']}", Fore.GREEN)
                    else:
                        # 用户取消了Docker配置，继续当前流程
                        self.colored_print("⚠️ Docker配置被取消，将继续不使用Docker", Fore.YELLOW)
                    
            else:
                # 没有现有配置，直接创建新配置
                self.colored_print("\n💡 未发现现有Docker配置，创建新配置", Fore.YELLOW)
                self.colored_print("🚀 跳转到Docker配置向导...", Fore.CYAN)
                docker_config_result = self.docker_wizard_setup(called_from_guided_setup=True)
                
                # Docker向导完成后，获取配置并应用到当前服务器
                if docker_config_result:
                    docker_configs = self.get_existing_docker_configs()
                    if docker_configs:
                        # 获取最新创建的配置
                        latest_config_name = list(docker_configs.keys())[-1]
                        latest_config = docker_configs[latest_config_name]
                        
                        if "specs" not in config["servers"][main_server_name]:
                            config["servers"][main_server_name]["specs"] = {}
                        config["servers"][main_server_name]["specs"]["docker"] = {
                            "container_name": latest_config['container_name'],
                            "image": latest_config['image'],
                            "auto_create": True,
                            "ports": latest_config.get('ports', []),
                            "volumes": latest_config.get('volumes', [])
                        }
                        self.colored_print(f"✅ 已应用Docker配置: {latest_config['container_name']}", Fore.GREEN)
                else:
                    # 用户取消了Docker配置，继续当前流程
                    self.colored_print("⚠️ Docker配置被取消，将继续不使用Docker", Fore.YELLOW)
        
        self.show_progress(4, 4, "完成配置")
        
        # 默认使用tmux - 使用SSH管理器期望的session格式
        config["servers"][main_server_name]["session"] = {
            "name": f"{main_server_name}_session",
            "working_directory": "~",
            "shell": "/bin/bash"
        }
        
        # 保存配置
        self.save_config(config)
        self.colored_print(f"\n{ConfigError.SUCCESS} 向导配置完成！", Fore.GREEN, Style.BRIGHT)
        self.colored_print(f"配置已保存到: {self.config_path}", Fore.GREEN)
    
    def template_setup(self):
        """模板配置 - 真正的填空式体验"""
        self.colored_print("\n📋 模板配置模式", Fore.YELLOW, Style.BRIGHT)
        self.colored_print("🚀 填空式快速配置 - 3分钟完成", Fore.YELLOW)
        self.colored_print("💡 基于最佳实践模板，只需修改关键参数", Fore.CYAN)
        self.colored_print("-" * 50, Fore.YELLOW)
        
        # 列出可用模板
        templates = list(self.templates_dir.glob("*.yaml"))
        if not templates:
            self.colored_print("❌ 没有找到模板文件", Fore.RED)
            return
        
        self.colored_print("\n📚 可用模板 (预设最佳实践):")
        template_descriptions = {
            "ssh_server": "🖥️  标准SSH服务器 - 适用于云服务器、VPS",
            "relay_server": "🔗 百度内网服务器 - 通过relay-cli连接",
            "docker_server": "🐳 Docker开发环境 - 容器化开发环境",
            "complex_server": "🚀 复杂ML环境 - GPU服务器 + Docker + 环境变量"
        }
        
        for i, template in enumerate(templates, 1):
            template_name = template.stem
            description = template_descriptions.get(template_name, "通用模板")
            self.colored_print(f"  {i}. {description}", Fore.GREEN)
        
        # 选择模板
        choice = self.smart_input(f"\n选择模板", 
                                validator=lambda x: 1 <= int(x) <= len(templates),
                                suggestions=[f"{i} ({templates[i-1].stem})" for i in range(1, min(4, len(templates)+1))])
        if not choice:
            return
            
        selected_template = templates[int(choice) - 1]
        
        # 加载并展示模板
        try:
            with open(selected_template, 'r', encoding='utf-8') as f:
                template_config = yaml.safe_load(f)
        except Exception as e:
            self.colored_print(f"{ConfigError.ERROR} 加载模板失败: {e}", Fore.RED)
            return
        
        self.colored_print(f"\n✨ 已选择模板: {selected_template.stem}", Fore.CYAN, Style.BRIGHT)
        self.colored_print("📋 模板预览:", Fore.CYAN)
        
        # 显示模板结构预览（简化版）
        if 'servers' in template_config:
            for server_name, server_config in template_config['servers'].items():
                self.colored_print(f"  服务器: {server_name}", Fore.YELLOW)
                self.colored_print(f"  类型: {server_config.get('type', 'unknown')}", Fore.WHITE)
                if 'container_name' in server_config:
                    self.colored_print(f"  Docker: {server_config['container_name']}", Fore.WHITE)
                self.colored_print(f"  描述: {server_config.get('description', '无')}", Fore.WHITE)
        
        self.colored_print(f"\n🔥 只需填空即可完成配置!", Fore.GREEN, Style.BRIGHT)
        
        # 简单填空式定制
        customized_config = self.quick_customize_template(template_config)
        
        # 保存配置
        if customized_config:
            self.save_config(customized_config)
            self.colored_print(f"\n{ConfigError.SUCCESS} 模板配置完成！", Fore.GREEN, Style.BRIGHT)
            self.colored_print(f"⚡ 耗时: <3分钟 | 配置文件: {self.config_path}", Fore.GREEN)
    
    def manual_setup(self):
        """手动配置 - 直接编辑配置文件"""
        self.colored_print("\n✏️ 手动配置模式", Fore.YELLOW, Style.BRIGHT)
        self.colored_print("直接编辑YAML配置文件", Fore.YELLOW)
        self.colored_print("-" * 30, Fore.YELLOW)
        
        # 创建配置文件（如果不存在）
        if not self.config_path.exists():
            template_config = self.get_config_template()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(template_config)
            self.colored_print("📄 已创建示例配置文件", Fore.GREEN)
        
        # 告诉用户配置文件位置
        absolute_path = self.config_path.resolve()
        self.colored_print(f"\n📍 配置文件路径:", Fore.CYAN, Style.BRIGHT)
        self.colored_print(f"   {absolute_path}", Fore.WHITE)
        
        self.colored_print(f"\n📝 编辑方式:", Fore.CYAN)
        self.colored_print(f"   - 使用任意文本编辑器编辑上述文件", Fore.WHITE)
        self.colored_print(f"   - 参考现有示例配置格式", Fore.WHITE)
        self.colored_print(f"   - 保存后可使用管理功能验证配置", Fore.WHITE)
        
        # 询问是否打开文件所在目录
        open_dir = self.smart_input("是否打开配置文件所在目录 (y/n)", 
                                   validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'] or x == '',
                                   default='n')
        
        if open_dir and open_dir.lower() in ['y', 'yes']:
            try:
                import platform
                if platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', str(self.config_dir)])
                elif platform.system() == 'Windows':  # Windows
                    subprocess.run(['explorer', str(self.config_dir)])
                else:  # Linux
                    subprocess.run(['xdg-open', str(self.config_dir)])
                self.colored_print("📁 已打开配置文件所在目录", Fore.GREEN)
            except Exception as e:
                self.colored_print(f"❌ 无法打开目录: {e}", Fore.RED)
    
    def get_config_template(self):
        """获取配置文件模板"""
        return """# Remote Terminal MCP Configuration
# 详细配置说明和示例

servers:
  # SSH直连示例
  ssh-server:
    host: "192.168.1.100"           # 服务器地址
    username: "ubuntu"              # 用户名
    port: 22                        # SSH端口
    private_key_path: "~/.ssh/id_rsa"
    type: "script_based"            # 连接类型
    description: "SSH direct connection"
    specs:
      connection:
        tool: "ssh"
        target:
          host: "192.168.1.100"
    
  # Relay连接示例
  relay-server:
    host: "internal-server.com"
    username: "work"                # 修正字段名
    port: 22
    private_key_path: "~/.ssh/id_rsa"
    type: "script_based"            # 修正类型
    description: "Internal server via relay-cli"
    specs:
      connection:
        tool: "relay-cli"
        target:
          host: "internal-server.com"
    
  # Docker服务器示例
  docker-server:
    host: "docker-host.com"
    username: "developer"               # 修正字段名
    port: 22
    private_key_path: "~/.ssh/id_rsa"
    type: "script_based"                # 修正类型
    description: "Docker development environment"
    specs:
      connection:
        tool: "ssh"
        target:
          host: "docker-host.com"
      docker:
        container_name: "dev_container"
        image: "ubuntu:20.04"
        auto_create: true
    session:
      name: "dev_session"
      working_directory: "~"
      shell: "/bin/bash"
    
  # 复杂配置示例
  complex-server:
    host: "ml-server.com"
    username: "researcher"              # 修正字段名
    port: 22
    private_key_path: "~/.ssh/id_rsa"
    type: "script_based"                # 修正类型
    description: "Complex ML development environment"
    specs:
      connection:
        tool: "relay-cli"
        target:
          host: "ml-server.com"
      docker:
        container_name: "pytorch_env"
        image: "pytorch/pytorch:latest"
        auto_create: true
      environment_setup:
        auto_setup: true
        environment:
          CUDA_VISIBLE_DEVICES: "0,1"
          PYTHONPATH: "/workspace"
        post_connect_commands:
          - "cd /workspace"
          - "source activate pytorch"
          - "echo 'ML environment ready!'"
    session:
      name: "ml_work"
      working_directory: "/workspace"
      shell: "/bin/bash"

# 配置字段说明:
# 
# 必填字段:
#   host: 服务器地址
#   username: 用户名 (修正为username)
#   type: 连接类型 (统一使用script_based)
#   description: 服务器描述
#   specs: 连接规格配置
#
# specs.connection字段:
#   tool: 连接工具 (ssh/relay-cli)
#   target.host: 目标服务器地址
#
# 其他字段:
#   relay_command: relay-cli命令
#
# Docker字段:
#   container_name: 容器名称
#   docker_image: Docker镜像
#   auto_create_container: 是否自动创建容器
#
# 可选字段:
#   tmux_session: tmux会话名
#   environment: 环境变量字典
#   post_connect_commands: 连接后执行的命令列表
#   jump_host: 跳板机地址
#   jump_user: 跳板机用户名
"""
    
    def quick_customize_template(self, template_config: Dict) -> Optional[Dict]:
        """快速填空式模板定制 - 只询问关键参数"""
        if not template_config.get('servers'):
            self.colored_print("❌ 模板格式错误", Fore.RED)
            return None
        
        customized = {"servers": {}}
        
        for server_name, server_config in template_config['servers'].items():
            self.colored_print(f"\n🎯 只需填写关键信息:", Fore.CYAN, Style.BRIGHT)
            
            # 只询问关键参数
            self.colored_print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", Fore.CYAN)
            
            # 1. 服务器名称
            new_name = self.smart_input("🏷️  服务器名称", 
                                      validator=lambda x: bool(x and len(x) > 0),
                                      suggestions=["gpu-server-1", "dev-server", "ml-server"],
                                      default=server_name.replace("example-", "my-"))
            if not new_name:
                return None
            
            # 2. 服务器地址
            new_host = self.smart_input("🌐 服务器地址", 
                                      validator=self.validate_hostname,
                                      suggestions=["192.168.1.100", "server.example.com"])
            if not new_host:
                return None
            
            # 3. 用户名
            new_user = self.smart_input("👤 用户名", 
                                      validator=self.validate_username,
                                      suggestions=["ubuntu", "root", os.getenv('USER', 'user')])
            if not new_user:
                return None
            
            # 复制模板配置，只替换关键参数
            new_config = server_config.copy()
            new_config.update({
                "host": new_host,
                "user": new_user,
                "description": f"Based on {server_config.get('type', 'template')}: {new_name}"
            })
            
            # 特殊处理：Relay命令
            if 'relay_command' in server_config:
                self.colored_print("🔗 检测到Relay连接，需要token", Fore.YELLOW)
                token = self.smart_input("🔑 Relay Token", 
                                       suggestions=["your-token-here"])
                if token:
                    new_config['relay_command'] = f"relay-cli -t {token} -s {new_host}"
                else:
                    new_config['relay_command'] = f"relay-cli -s {new_host}"
            
            # 特殊处理：容器名称
            if 'container_name' in server_config:
                self.colored_print("🐳 检测到Docker配置，使用个性化容器名", Fore.YELLOW)
                container_name = self.smart_input("📦 容器名称",
                                                default=f"{new_user}_{server_config.get('container_name', 'dev')}",
                                                suggestions=[f"{new_user}_dev", f"{new_user}_pytorch"])
                if container_name:
                    new_config['container_name'] = container_name
            
            customized["servers"][new_name] = new_config
            
            # 显示生成的配置摘要
            self.colored_print(f"\n✅ 配置摘要:", Fore.GREEN)
            self.colored_print(f"   服务器: {new_name} → {new_host}", Fore.WHITE)  
            self.colored_print(f"   用户: {new_user}", Fore.WHITE)
            self.colored_print(f"   类型: {new_config.get('type', 'unknown')}", Fore.WHITE)
            if 'container_name' in new_config:
                self.colored_print(f"   Docker: {new_config['container_name']}", Fore.WHITE)
            
        return customized

    def customize_template(self, template_config: Dict) -> Optional[Dict]:
        """详细模板定制 - 用于向导模式"""
        if not template_config.get('servers'):
            self.colored_print("❌ 模板格式错误", Fore.RED)
            return None
        
        customized = {"servers": {}}
        
        for server_name, server_config in template_config['servers'].items():
            self.colored_print(f"\n定制服务器: {server_name}", Fore.CYAN)
            
            # 基本信息
            new_name = self.smart_input(f"服务器名称 [{server_name}]: ", default=server_name)
            new_host = self.smart_input(f"服务器地址 [{server_config.get('host', '')}]: ", default=server_config.get('host', ''))
            new_user = self.smart_input(f"用户名 [{server_config.get('user', '')}]: ", default=server_config.get('user', ''))
            
            # 复制原配置
            new_config = server_config.copy()
            new_config['host'] = new_host
            new_config['user'] = new_user
            
            # 特殊字段处理
            if 'relay_command' in server_config:
                current_cmd = server_config['relay_command']
                new_cmd = self.smart_input(f"Relay命令 [{current_cmd}]: ", default=current_cmd)
                new_config['relay_command'] = new_cmd
            
            if 'container_name' in server_config:
                current_container = server_config['container_name']
                new_container = self.smart_input(f"容器名称 [{current_container}]: ", default=current_container)
                new_config['container_name'] = new_container
            
            customized['servers'][new_name] = new_config
        
        return customized
    
    def manage_existing(self):
        """管理现有配置"""
        if not self.config_path.exists():
            self.colored_print("❌ 配置文件不存在", Fore.RED)
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            self.colored_print(f"{ConfigError.ERROR} 读取配置文件失败: {e}", Fore.RED)
            return
        
        servers = config.get('servers', {})
        if not servers:
            self.colored_print("❌ 没有配置的服务器", Fore.RED)
            return
        
        self.colored_print("\n📋 现有服务器配置:", Fore.CYAN)
        server_list = list(servers.keys())
        for i, server_name in enumerate(server_list, 1):
            server_info = servers[server_name]
            self.colored_print(f"{i}. {server_name} - {server_info.get('description', '无描述')}", Fore.GREEN)
        
        self.colored_print("\n操作选项:", Fore.CYAN)
        self.colored_print("1. 查看详细配置")
        self.colored_print("2. 删除服务器")
        self.colored_print("3. 导出配置")
        self.colored_print("0. 返回主菜单")
        
        choice = self.smart_input("选择操作")
        
        if choice == "1":
            # 查看详细配置
            server_idx = int(self.smart_input(f"选择服务器 (1-{len(server_list)})", validator=lambda x: x.isdigit() and 1 <= int(x) <= len(server_list))) - 1
            if 0 <= server_idx < len(server_list):
                server_name = server_list[server_idx]
                self.colored_print(f"\n{server_name} 详细配置:")
                self.colored_print(yaml.dump({server_name: servers[server_name]}, default_flow_style=False))
        
        elif choice == "2":
            # 删除服务器
            server_idx = int(self.smart_input(f"选择要删除的服务器 (1-{len(server_list)})", validator=lambda x: x.isdigit() and 1 <= int(x) <= len(server_list))) - 1
            if 0 <= server_idx < len(server_list):
                server_name = server_list[server_idx]
                if self.smart_input(f"确认删除服务器 {server_name}?", validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'], suggestions=['y', 'n'], default='n') == 'y':
                    del config['servers'][server_name]
                    self.save_config(config, merge_mode=False)
                    self.colored_print(f"✅ 已删除服务器 {server_name}", Fore.GREEN)
        
        elif choice == "3":
            # 导出配置
            export_path = self.smart_input("导出文件路径 [config_backup.yaml]", default="config_backup.yaml")
            try:
                with open(export_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                self.colored_print(f"✅ 配置已导出到 {export_path}", Fore.GREEN)
            except Exception as e:
                self.colored_print(f"{ConfigError.ERROR} 导出失败: {e}", Fore.RED)
    
    def test_connection(self):
        """测试连接"""
        if not self.config_path.exists():
            self.colored_print("❌ 配置文件不存在", Fore.RED)
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            self.colored_print(f"{ConfigError.ERROR} 读取配置文件失败: {e}", Fore.RED)
            return
        
        servers = config.get('servers', {})
        if not servers:
            self.colored_print("❌ 没有配置的服务器", Fore.RED)
            return
        
        self.colored_print("\n🔍 测试服务器连接:", Fore.CYAN)
        server_list = list(servers.keys())
        for i, server_name in enumerate(server_list, 1):
            self.colored_print(f"{i}. {server_name}", Fore.GREEN)
        
        try:
            choice = int(self.smart_input(f"选择要测试的服务器 (1-{len(server_list)})", validator=lambda x: x.isdigit() and 1 <= int(x) <= len(server_list)))
            if 1 <= choice <= len(server_list):
                server_name = server_list[choice - 1]
                self.colored_print(f"正在测试连接到 {server_name}...", Fore.CYAN)
                # 这里可以调用实际的连接测试逻辑
                self.colored_print("💡 提示: 连接测试功能需要集成到主程序中", Fore.YELLOW)
            else:
                self.colored_print(f"{ConfigError.ERROR} 无效选择", Fore.RED)
        except ValueError:
            self.colored_print(f"{ConfigError.ERROR} 请输入数字", Fore.RED)
    
    def save_config(self, config: Dict, merge_mode: bool = True):
        """保存配置 - 合并到现有配置而不是覆盖"""
        try:
            # 读取现有配置
            existing_config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f) or {}
            
            # 确保servers节点存在
            if 'servers' not in existing_config:
                existing_config['servers'] = {}
            
            # 合并新的服务器配置到现有配置
            if 'servers' in config:
                existing_config['servers'].update(config['servers'])
            
            # 合并其他配置项
            for key, value in config.items():
                if key != 'servers':
                    existing_config[key] = value
            
            # 保存合并后的配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(existing_config, f, default_flow_style=False, allow_unicode=True)
                
        except Exception as e:
            self.colored_print(f"{ConfigError.ERROR} 保存配置失败: {e}", Fore.RED)
            raise
    
    def show_existing_configurations_overview(self):
        """显示现有配置概览（用于服务器配置）"""
        # 显示现有服务器配置
        existing_servers = self.get_existing_servers()
        if existing_servers:
            self.colored_print("\n📋 现有服务器配置:", Fore.GREEN, Style.BRIGHT)
            for server_name, server_info in existing_servers.items():
                # 获取服务器类型，并转换为友好显示
                server_type = server_info.get('type', 'unknown')
                connection_type = server_info.get('connection_type', 'ssh')  # 默认ssh
                host = server_info.get('host', 'unknown')
                has_docker = 'docker' in server_info
                docker_indicator = " [🐳]" if has_docker else ""
                
                # 根据连接类型显示友好的描述
                if connection_type == 'relay':
                    type_display = "Relay中继"
                elif connection_type == 'ssh':
                    type_display = "SSH直连"
                else:
                    type_display = server_type if server_type != 'unknown' else connection_type
                
                self.colored_print(f"  • {server_name} - {type_display}: {host}{docker_indicator}", Fore.WHITE)
        
        # 显示现有Docker配置
        existing_docker_configs = self.get_existing_docker_configs()
        if existing_docker_configs:
            self.colored_print("\n🐳 现有Docker配置:", Fore.BLUE, Style.BRIGHT)
            for config_name, config_info in existing_docker_configs.items():
                image = config_info.get('image', 'unknown')
                container_name = config_info.get('container_name', config_name)
                self.colored_print(f"  • {container_name} - {image}", Fore.WHITE)
        
        if not existing_servers and not existing_docker_configs:
            self.colored_print("\n💡 当前无现有配置，开始创建第一个配置", Fore.YELLOW)
        
        self.colored_print("")  # 空行分隔
    
    def show_existing_docker_overview(self, called_from_wizard=False):
        """显示现有Docker配置概览（专用于Docker配置界面）"""
        existing_docker_configs = self.get_existing_docker_configs()
        
        if existing_docker_configs:
            self.colored_print("\n🐳 现有Docker容器配置:", Fore.BLUE, Style.BRIGHT)
            for config_name, config_info in existing_docker_configs.items():
                image = config_info.get('image', 'unknown')
                container_name = config_info.get('container_name', config_name)
                ports = config_info.get('ports', [])
                port_info = f" [{','.join(ports)}]" if ports else ""
                self.colored_print(f"  • {container_name} - {image}{port_info}", Fore.WHITE)
            
            # 给用户选择是否继续的机会
            self.colored_print("\n📋 操作选项:", Fore.CYAN)
            self.colored_print("  1. 继续创建新的Docker配置", Fore.GREEN)
            self.colored_print("  2. 管理现有Docker配置", Fore.BLUE)
            if called_from_wizard:
                self.colored_print("  0. 返回上一级", Fore.WHITE)
            else:
                self.colored_print("  0. 返回主菜单", Fore.WHITE)
            
            choice = self.smart_input("选择操作", 
                                    validator=lambda x: x in ['0', '1', '2'],
                                    show_suggestions=False)
            
            if choice == "0":
                return False  # 返回上一级或主菜单
            elif choice == "2":
                self.manage_docker_configs()
                return False  # 管理完成后返回
            # choice == "1" 继续创建流程
            
        else:
            self.colored_print("\n💡 当前无现有Docker配置，开始创建第一个Docker容器环境", Fore.YELLOW)
        
        self.colored_print("")  # 空行分隔
        return True  # 继续创建流程
    
    def get_existing_servers(self) -> dict:
        """获取现有服务器配置"""
        try:
            if not os.path.exists(self.config_path):
                return {}
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            return config.get('servers', {}) if config else {}
        except Exception:
            return {}
    
    def get_existing_docker_configs(self) -> dict:
        """获取现有Docker配置"""
        try:
            docker_templates_dir = self.config_dir / "docker_templates"
            if not docker_templates_dir.exists():
                return {}
            
            docker_configs = {}
            for config_file in docker_templates_dir.glob("*.yaml"):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config and 'docker' in config:
                        docker_configs[config_file.stem] = config['docker']
            
            return docker_configs
        except Exception:
            return {}
    
    def validate_container_name(self, name: str) -> bool:
        """验证容器名称（检查是否为空和是否重复）"""
        if not name or len(name.strip()) == 0:
            self.colored_print("❌ 容器名称不能为空", Fore.RED)
            return False
        
        name = name.strip()
        
        # 检查Docker配置重复性
        existing_docker_configs = self.get_existing_docker_configs()
        if name in existing_docker_configs:
            self.colored_print(f"❌ 容器名称 '{name}' 已存在，请选择其他名称", Fore.RED)
            return False
        
        # 检查服务器配置中的Docker容器名重复性
        existing_servers = self.get_existing_servers()
        for server_name, server_config in existing_servers.items():
            if 'docker' in server_config:
                existing_container_name = server_config['docker'].get('container_name')
                if existing_container_name == name:
                    self.colored_print(f"❌ 容器名称 '{name}' 已在服务器 '{server_name}' 中使用，请选择其他名称", Fore.RED)
                    return False
        
        return True

    def validate_config(self) -> bool:
        """验证配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not isinstance(config, dict):
                self.colored_print(f"{ConfigError.ERROR} 配置文件格式错误：根节点必须是字典", Fore.RED)
                return False
            
            if 'servers' not in config:
                self.colored_print(f"{ConfigError.ERROR} 配置文件格式错误：缺少 servers 节点", Fore.RED)
                return False
            
            servers = config['servers']
            if not isinstance(servers, dict):
                self.colored_print(f"{ConfigError.ERROR} 配置文件格式错误：servers 必须是字典", Fore.RED)
                return False
            
            for server_name, server_config in servers.items():
                if not isinstance(server_config, dict):
                    self.colored_print(f"{ConfigError.ERROR} 服务器 {server_name} 配置格式错误", Fore.RED)
                    return False
                
                required_fields = ['host', 'user', 'type']
                for field in required_fields:
                    if field not in server_config:
                        self.colored_print(f"{ConfigError.ERROR} 服务器 {server_name} 缺少必填字段: {field}", Fore.RED)
                        return False
            
            return True
            
        except yaml.YAMLError as e:
            self.colored_print(f"{ConfigError.ERROR} YAML语法错误: {e}", Fore.RED)
            return False
        except Exception as e:
            self.colored_print(f"{ConfigError.ERROR} 验证配置文件失败: {e}", Fore.RED)
            return False

    def docker_wizard_setup(self, called_from_guided_setup=False):
        """Docker容器环境向导配置"""
        self.colored_print("\n🐳 Docker容器环境向导配置", Fore.CYAN, Style.BRIGHT)
        self.colored_print("=" * 50, Fore.CYAN)
        self.colored_print("通过简单的向导来配置你的Docker容器环境", Fore.CYAN)
        self.colored_print("-" * 50, Fore.CYAN)
        
        # 显示现有Docker配置概览
        if not self.show_existing_docker_overview(called_from_wizard=called_from_guided_setup):
            return False  # 用户选择退出
        
        # 步骤1: 基本信息
        self.show_progress(1, 3, "基本容器信息")
        
        container_name = self.smart_input("容器名称", 
                                        validator=lambda x: self.validate_container_name(x),
                                        suggestions=["dev-container", "ml-workspace", "web-dev"])
        if not container_name:
            return False
            
        docker_image = self.smart_input("Docker镜像", 
                                      validator=lambda x: bool(x and len(x) > 0),
                                      suggestions=["ubuntu:20.04", "xxx.com/namespace/ubuntu_dev:latest", "pytorch/pytorch:latest", "node:18-alpine"],
                                      default="ubuntu:20.04")
        if not docker_image:
            return False
        
        # 步骤2: BOS环境配置  
        self.show_progress(2, 3, "BOS环境配置")
        
        self.colored_print("\n☁️ BOS (百度对象存储)环境配置", Fore.BLUE)
        self.colored_print("💡 配置BOS环境可以方便地同步你的配置文件到容器中", Fore.YELLOW)
        self.colored_print("   例如: .zshrc, .p10k.zsh, .vimrc 等个人配置文件", Fore.YELLOW)
        
        setup_bos = self.smart_input("是否配置BOS环境", 
                                   validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
                                   suggestions=['y', 'n'],
                                   default='n')
        if not setup_bos:
            return False
            
        use_bos = setup_bos.lower() in ['y', 'yes']
        
        bos_config = {}
        if use_bos:
            self.colored_print("\n请输入BOS配置信息:", Fore.BLUE)
            
            bos_ak = self.smart_input("BOS AccessKey (AK)", 
                                    validator=lambda x: bool(x and len(x) > 0),
                                    suggestions=["your-access-key"])
            if not bos_ak:
                return False
                
            bos_sk = self.smart_input("BOS SecretKey (SK)", 
                                    validator=lambda x: bool(x and len(x) > 0),
                                    suggestions=["your-secret-key"])
            if not bos_sk:
                return False
                
            bos_template_path = self.smart_input("BOS配置文件模板存放路径 (远端BOS路径)", 
                                             default="bos://your-bucket/username/templates/",
                                             suggestions=["bos://your-bucket/username/templates/", "bos://work-bucket/user/config/"])
            if not bos_template_path:
                return False
                
            bos_config = {
                "access_key": bos_ak,
                "secret_key": bos_sk,
                "template_path": bos_template_path,
                "local_config_path": "/root/.bos/config"
            }
        
        # 步骤3: 生成配置
        self.show_progress(3, 3, "生成Docker配置")
        
        # 使用预设的端口和挂载配置
        ports = ["8080:8080", "8888:8888", "6006:6006"]  # 常用端口：web服务、jupyter、tensorboard
        volumes = ["/home:/home", "/data:/data"]  # 常用挂载目录
        
        # 构建Docker配置
        docker_config = {
            "container_name": container_name,
            "image": docker_image,
            "auto_create": True,
            "ports": ports,
            "volumes": volumes,
            "working_directory": "/workspace",
            "privileged": True,
            "network_mode": "bridge",
            "restart_policy": "unless-stopped",
            "environment": {},
            "setup_commands": []
        }
        
        # 添加基础开发工具
        docker_config["setup_commands"].extend([
            "apt-get update",
            "apt-get install -y curl git vim wget"
        ])
        
        # 添加BOS配置
        if use_bos and bos_config:
            bos_setup_commands = [
                "pip install boscli",
                f"mkdir -p {os.path.dirname(bos_config['local_config_path'])}",
                f"echo '[Credentials]' > {bos_config['local_config_path']}",
                f"echo 'bos_access_key_id = {bos_config['access_key']}' >> {bos_config['local_config_path']}",
                f"echo 'bos_secret_access_key = {bos_config['secret_key']}' >> {bos_config['local_config_path']}",
                f"# 同步配置文件模板: bos sync {bos_config['template_path']} /root/",
                "echo '# 使用 bos sync 命令同步你的配置文件模板到容器' >> /root/.bashrc"
            ]
            docker_config["setup_commands"].extend(bos_setup_commands)
            docker_config["environment"]["BOS_CONFIG_PATH"] = bos_config["local_config_path"]
            docker_config["environment"]["BOS_TEMPLATE_PATH"] = bos_config["template_path"]
        
        # 显示配置预览
        self.colored_print("\n✅ Docker配置生成完成！", Fore.GREEN, Style.BRIGHT)
        self.colored_print("=" * 50, Fore.GREEN)
        self.colored_print(f"容器名称: {container_name}", Fore.WHITE)
        self.colored_print(f"镜像: {docker_image}", Fore.WHITE)
        self.colored_print(f"BOS环境: {'已配置' if use_bos else '未配置'}", Fore.WHITE)
        self.colored_print(f"端口映射: {', '.join(ports) if ports else '无'}", Fore.WHITE)
        self.colored_print(f"目录挂载: {', '.join(volumes) if volumes else '无'}", Fore.WHITE)
        
        # 询问是否保存配置
        self.colored_print("\n💾 配置处理选项:", Fore.CYAN)
        self.colored_print("  1. 保存Docker配置", Fore.GREEN)
        self.colored_print("  2. 创建完整服务器配置(包含Docker)", Fore.BLUE)
        self.colored_print("  3. 仅预览Docker运行命令", Fore.YELLOW)
        self.colored_print("  0. 返回主菜单", Fore.WHITE)
        
        save_choice = self.smart_input("选择操作", 
                                     validator=lambda x: x in ['0', '1', '2', '3'])
        
        if save_choice == "1":
            # 保存Docker配置
            self.save_docker_wizard_config(docker_config)
            return True  # 配置成功创建
        elif save_choice == "2":
            # 创建完整服务器配置
            self.create_server_with_docker_wizard(docker_config)
            return True  # 配置成功创建
        elif save_choice == "3":
            # 预览Docker命令
            self.preview_docker_wizard_command(docker_config)
            return True  # 仅预览，但可以认为是成功
        else:
            return False  # 用户选择返回或取消
            
    def save_docker_wizard_config(self, docker_config: dict):
        """保存Docker向导配置"""
        config_name = docker_config["container_name"]
        docker_templates_dir = self.config_dir / "docker_templates"
        docker_templates_dir.mkdir(exist_ok=True)
        
        config_file = docker_templates_dir / f"{config_name}.yaml"
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump({"docker": docker_config}, f, default_flow_style=False, allow_unicode=True)
        
        self.colored_print(f"\n✅ Docker配置已保存: {config_file}", Fore.GREEN, Style.BRIGHT)
        
    def create_server_with_docker_wizard(self, docker_config: dict):
        """使用Docker向导配置创建完整服务器配置"""
        self.colored_print("\n🚀 创建包含Docker的服务器配置", Fore.GREEN, Style.BRIGHT)
        self.colored_print("-" * 40, Fore.GREEN)
        
        # 基本服务器信息
        server_name = self.smart_input("服务器名称", 
                                     validator=lambda x: bool(x and len(x) > 0),
                                     suggestions=[f"{docker_config['container_name']}_server", "docker_server"],
                                     default=f"{docker_config['container_name']}_server")
        
        server_host = self.smart_input("服务器地址", 
                                     validator=self.validate_hostname,
                                     suggestions=["192.168.1.100", "your-server.com"])
        
        username = self.smart_input("用户名", 
                                   validator=self.validate_username,
                                   suggestions=["ubuntu", "root", os.getenv('USER', 'user')],
                                   default="ubuntu")
        
        # 生成完整服务器配置
        config = {"servers": {server_name: {
            "host": server_host,
            "username": username,
            "port": 22,
            "private_key_path": "~/.ssh/id_rsa",
            "type": "docker",
            "description": f"Docker服务器配置: {docker_config['container_name']}",
            "docker": docker_config,
                         "session": {
                 "name": f"{server_name}_session",
                 "working_directory": docker_config.get("working_directory", "/workspace"),
                 "shell": "/bin/bash"
             }
        }}}
        
        # 保存配置
        self.save_config(config)
        self.colored_print(f"\n✅ 服务器配置 '{server_name}' 创建成功！", Fore.GREEN, Style.BRIGHT)
        self.colored_print(f"已集成Docker环境: {docker_config['container_name']}", Fore.GREEN)
        
    def preview_docker_wizard_command(self, docker_config: dict):
        """预览Docker向导生成的运行命令"""
        self.colored_print("\n🔍 Docker运行命令预览", Fore.CYAN, Style.BRIGHT)
        self.colored_print("=" * 60, Fore.CYAN)
        
        # 构建docker run命令
        cmd_parts = ["docker run -d"]
        
        # 容器名称
        cmd_parts.append(f"--name {docker_config['container_name']}")
        
        # 端口映射
        for port in docker_config.get('ports', []):
            cmd_parts.append(f"-p {port}")
        
        # 目录挂载
        for volume in docker_config.get('volumes', []):
            cmd_parts.append(f"-v {volume}")
        
        # 环境变量
        for key, value in docker_config.get('environment', {}).items():
            cmd_parts.append(f"-e {key}={value}")
        
        # 其他配置
        if docker_config.get('privileged'):
            cmd_parts.append("--privileged")
        if docker_config.get('network_mode'):
            cmd_parts.append(f"--network {docker_config['network_mode']}")
        if docker_config.get('restart_policy'):
            cmd_parts.append(f"--restart {docker_config['restart_policy']}")
        if docker_config.get('working_directory'):
            cmd_parts.append(f"-w {docker_config['working_directory']}")
        
        # 镜像
        cmd_parts.append(docker_config['image'])
        
        # 默认命令
        cmd_parts.append("/bin/bash -c 'tail -f /dev/null'")
        
        # 显示命令
        docker_command = " \\\n  ".join(cmd_parts)
        self.colored_print(docker_command, Fore.WHITE)
        
        # 显示设置命令
        if docker_config.get('setup_commands'):
            self.colored_print(f"\n📋 容器创建后的设置命令:", Fore.GREEN)
            for i, cmd in enumerate(docker_config['setup_commands'], 1):
                self.colored_print(f"  {i}. {cmd}", Fore.WHITE)
        
        self.colored_print("\n" + "=" * 60, Fore.CYAN)
    
    def manage_docker_configs(self):
        """管理现有Docker配置"""
        self.colored_print("\n🐳 Docker配置管理", Fore.CYAN, Style.BRIGHT)
        self.colored_print("=" * 40, Fore.CYAN)
        
        existing_docker_configs = self.get_existing_docker_configs()
        if not existing_docker_configs:
            self.colored_print("❌ 没有找到Docker配置", Fore.RED)
            return
        
        self.colored_print("\n📋 现有Docker配置:", Fore.GREEN)
        config_list = list(existing_docker_configs.items())
        for i, (config_name, config_info) in enumerate(config_list, 1):
            image = config_info.get('image', 'unknown')
            container_name = config_info.get('container_name', config_name)
            self.colored_print(f"  {i}. {container_name} - {image}", Fore.WHITE)
        
        self.colored_print("\n操作选项:", Fore.CYAN)
        self.colored_print("  1. 查看详细配置", Fore.GREEN)
        self.colored_print("  2. 删除Docker配置", Fore.RED)
        self.colored_print("  3. 预览Docker命令", Fore.YELLOW)
        self.colored_print("  0. 返回", Fore.WHITE)
        
        choice = self.smart_input("选择操作", 
                                validator=lambda x: x in ['0', '1', '2', '3'],
                                show_suggestions=False)
        
        if choice == "0":
            return
        elif choice in ['1', '2', '3']:
            config_choice = self.smart_input(f"选择Docker配置 (1-{len(config_list)})", 
                                          validator=lambda x: x.isdigit() and 1 <= int(x) <= len(config_list))
            if not config_choice:
                return
                
            config_name, config_info = config_list[int(config_choice) - 1]
            
            if choice == "1":
                # 查看详细配置
                self.colored_print(f"\n📋 Docker配置详情: {config_name}", Fore.CYAN, Style.BRIGHT)
                self.colored_print("-" * 40, Fore.CYAN)
                for key, value in config_info.items():
                    self.colored_print(f"{key}: {value}", Fore.WHITE)
            elif choice == "2":
                # 删除配置
                confirm = self.smart_input(f"确认删除Docker配置 '{config_name}' (y/n)", 
                                         validator=lambda x: x.lower() in ['y', 'n'])
                if confirm and confirm.lower() == 'y':
                    docker_templates_dir = self.config_dir / "docker_templates"
                    config_file = docker_templates_dir / f"{config_name}.yaml"
                    if config_file.exists():
                        config_file.unlink()
                        self.colored_print(f"✅ Docker配置 '{config_name}' 已删除", Fore.GREEN)
                    else:
                        self.colored_print(f"❌ 配置文件不存在", Fore.RED)
            elif choice == "3":
                # 预览Docker命令
                self.preview_docker_wizard_command(config_info)
    
    def integrate_docker_to_server(self):
        """将Docker环境集成到服务器配置"""
        self.colored_print("\n🔗 Docker环境集成到服务器", Fore.CYAN, Style.BRIGHT)
        self.colored_print("-" * 40, Fore.CYAN)
        
        # 首先列出现有的Docker配置
        docker_configs = self.docker_manager.list_docker_configs()
        if not docker_configs:
            self.colored_print("❌ 没有找到Docker配置，请先创建Docker环境", Fore.RED)
            return
        
        self.colored_print("📋 可用的Docker环境:", Fore.GREEN)
        for i, config_name in enumerate(docker_configs, 1):
            self.colored_print(f"  {i}. {config_name}", Fore.WHITE)
        
        # 选择Docker配置
        while True:
            try:
                choice = int(self.smart_input(f"选择Docker环境 (1-{len(docker_configs)})", 
                                            validator=lambda x: x.isdigit() and 1 <= int(x) <= len(docker_configs)))
                selected_docker = docker_configs[int(choice) - 1]
                break
            except (ValueError, IndexError):
                self.colored_print("❌ 无效选择", Fore.RED)
        
        # 获取Docker配置详情
        docker_config = self.docker_manager.get_docker_config(selected_docker)
        if not docker_config:
            self.colored_print("❌ 无法加载Docker配置", Fore.RED)
            return
        
        # 选择服务器配置方式
        self.colored_print(f"\n✅ 已选择Docker环境: {selected_docker}", Fore.GREEN)
        self.colored_print("\n配置服务器选项:", Fore.CYAN)
        self.colored_print("  1. 创建新服务器配置 (包含Docker)", Fore.GREEN)
        self.colored_print("  2. 添加到现有服务器配置", Fore.BLUE)
        
        server_choice = self.smart_input("选择方式", 
                                       validator=lambda x: x in ['1', '2'])
        
        if server_choice == "1":
            self.create_server_with_docker(docker_config)
        elif server_choice == "2":
            self.add_docker_to_existing_server(docker_config)
    
    def create_server_with_docker(self, docker_config: DockerEnvironmentConfig):
        """创建包含Docker的新服务器配置"""
        self.colored_print("\n🚀 创建包含Docker的服务器配置", Fore.GREEN, Style.BRIGHT)
        self.colored_print("-" * 40, Fore.GREEN)
        
        # 基本服务器信息
        server_name = self.smart_input("服务器名称", 
                                     validator=lambda x: bool(x and len(x) > 0),
                                     suggestions=[f"{docker_config.container_name}_server", "docker_server"])
        
        server_host = self.smart_input("服务器地址", 
                                     validator=self.validate_hostname,
                                     suggestions=["192.168.1.100", "your-server.com"])
        
        username = self.smart_input("用户名", 
                                   validator=self.validate_username,
                                   suggestions=["ubuntu", "root", os.getenv('USER', 'user')])
        
        # 生成配置
        config = {"servers": {server_name: {
            "host": server_host,
            "username": username,
            "port": 22,
            "private_key_path": "~/.ssh/id_rsa",
            "type": "script_based",
            "description": f"服务器配置与Docker环境: {docker_config.container_name}",
            "specs": {
                "connection": {
                    "tool": "ssh",
                    "target": {"host": server_host}
                },
                "docker": docker_config.to_yaml_dict()
            },
            "session": {
                "name": f"{server_name}_session",
                "working_directory": docker_config.working_directory,
                "shell": "/bin/bash"
            }
        }}}
        
        # 保存配置
        self.save_config(config)
        self.colored_print(f"\n✅ 服务器配置 '{server_name}' 创建成功！", Fore.GREEN, Style.BRIGHT)
        self.colored_print(f"已集成Docker环境: {docker_config.container_name}", Fore.GREEN)
    
    def add_docker_to_existing_server(self, docker_config: DockerEnvironmentConfig):
        """添加Docker配置到现有服务器"""
        # TODO: 实现添加到现有服务器的功能
        self.colored_print("🚧 添加到现有服务器功能正在开发中...", Fore.YELLOW)
    
    def enhanced_docker_configuration(self, server_name: str) -> dict:
        """增强版Docker配置 - 集成到服务器配置流程"""
        self.colored_print(f"\n🐳 为服务器 '{server_name}' 配置Docker环境", Fore.CYAN, Style.BRIGHT)
        self.colored_print("-" * 50, Fore.CYAN)
        
        # 选择配置方式
        self.colored_print("Docker配置方式:", Fore.GREEN)
        self.colored_print("  1. 快速配置 (基础容器设置)", Fore.GREEN)
        self.colored_print("  2. 使用Docker模板", Fore.BLUE)
        self.colored_print("  3. 详细自定义配置", Fore.YELLOW)
        self.colored_print("  4. 从现有Docker配置选择", Fore.MAGENTA)
        
        docker_choice = self.smart_input("选择Docker配置方式", 
                                       validator=lambda x: x in ['1', '2', '3', '4'])
        
        if docker_choice == "1":
            return self.quick_docker_config(server_name)
        elif docker_choice == "2":
            return self.template_docker_config(server_name)
        elif docker_choice == "3":
            return self.detailed_docker_config(server_name)
        elif docker_choice == "4":
            return self.existing_docker_config(server_name)
        
        return {}
    
    def quick_docker_config(self, server_name: str) -> dict:
        """快速Docker配置"""
        self.colored_print("\n⚡ 快速Docker配置", Fore.GREEN, Style.BRIGHT)
        
        container_name = self.smart_input("容器名称", 
                                        default=f"{server_name}_container",
                                        suggestions=[f"{server_name}_dev", f"{server_name}_work"])
        
        image = self.smart_input("Docker镜像", 
                               default="ubuntu:20.04",
                               suggestions=["ubuntu:20.04", "pytorch/pytorch:latest", "node:16-alpine"])
        
        use_gpu = self.smart_input("是否启用GPU支持 (y/n)", 
                                 default="n",
                                 validator=lambda x: x.lower() in ['y', 'n']).lower() == 'y'
        
        return {
            "container_name": container_name,
            "image": image,
            "auto_create": True,
            "working_directory": "/workspace",
            "privileged": True,
            "network_mode": "host",
            "restart_policy": "always",
            "gpus": "all" if use_gpu else "",
            "shm_size": "64g" if use_gpu else "8g",
            "volumes": ["/home:/home", "/data:/data"] if use_gpu else ["/home:/home"]
        }
    
    def template_docker_config(self, server_name: str) -> dict:
        """基于模板的Docker配置"""
        self.colored_print("\n📋 基于模板的Docker配置", Fore.BLUE, Style.BRIGHT)
        
        # 调用Docker管理器的模板功能
        templates_dir = self.docker_manager.docker_templates_dir
        templates = list(templates_dir.glob("*.yaml"))
        
        if not templates:
            self.colored_print("❌ 没有找到Docker模板", Fore.RED)
            return {}
        
        self.colored_print("可用模板:", Fore.CYAN)
        for i, template in enumerate(templates, 1):
            try:
                with open(template, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                template_type = config.get('template_type', 'unknown')
                description = config.get('description', '无描述')
                self.colored_print(f"  {i}. {template.stem} ({template_type}) - {description}", Fore.WHITE)
            except Exception:
                self.colored_print(f"  {i}. {template.stem} (读取失败)", Fore.RED)
        
        # 选择模板
        while True:
            try:
                choice = int(self.smart_input(f"选择模板 (1-{len(templates)})", 
                                            validator=lambda x: x.isdigit() and 1 <= int(x) <= len(templates)))
                selected_template = templates[int(choice) - 1]
                break
            except (ValueError, IndexError):
                self.colored_print("❌ 无效选择", Fore.RED)
        
        # 加载模板配置
        try:
            with open(selected_template, 'r', encoding='utf-8') as f:
                template_config = yaml.safe_load(f)
            
            # 自定义容器名称
            container_name = self.smart_input("容器名称", 
                                            default=f"{server_name}_{template_config.get('container_name', 'container')}")
            template_config["container_name"] = container_name
            
            return template_config
            
        except Exception as e:
            self.colored_print(f"❌ 加载模板失败: {e}", Fore.RED)
            return {}
    
    def detailed_docker_config(self, server_name: str) -> dict:
        """详细Docker配置"""
        self.colored_print("\n⚙️ 详细Docker配置", Fore.YELLOW, Style.BRIGHT)
        self.colored_print("🔄 跳转到Docker配置管理器...", Fore.CYAN)
        
        # 调用独立的Docker配置管理器
        self.docker_manager.create_custom_environment()
        
        # 获取最新创建的配置
        docker_configs = self.docker_manager.list_docker_configs()
        if docker_configs:
            latest_config = self.docker_manager.get_docker_config(docker_configs[-1])
            if latest_config:
                return latest_config.to_yaml_dict()
        
        return {}
    
    def existing_docker_config(self, server_name: str) -> dict:
        """选择现有Docker配置"""
        self.colored_print("\n📂 选择现有Docker配置", Fore.MAGENTA, Style.BRIGHT)
        
        docker_configs = self.docker_manager.list_docker_configs()
        if not docker_configs:
            self.colored_print("❌ 没有找到Docker配置，请先创建", Fore.RED)
            return {}
        
        self.colored_print("现有Docker配置:", Fore.CYAN)
        for i, config_name in enumerate(docker_configs, 1):
            self.colored_print(f"  {i}. {config_name}", Fore.WHITE)
        
        while True:
            try:
                choice = int(self.smart_input(f"选择配置 (1-{len(docker_configs)})", 
                                            validator=lambda x: x.isdigit() and 1 <= int(x) <= len(docker_configs)))
                selected_config = docker_configs[int(choice) - 1]
                break
            except (ValueError, IndexError):
                self.colored_print("❌ 无效选择", Fore.RED)
        
        docker_config = self.docker_manager.get_docker_config(selected_config)
        if docker_config:
            return docker_config.to_yaml_dict()
        
        return {}

def main():
    """主函数"""
    config_manager = EnhancedConfigManager()
    config_manager.main_menu()

if __name__ == "__main__":
    main()