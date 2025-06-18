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
import time
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
# Docker配置现在统一在enhanced_config_manager中处理

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
        """初始化配置管理器"""
        # 检测是否在MCP环境中运行
        self.is_mcp_mode = (
            os.environ.get('NO_COLOR') == '1' or 
            os.environ.get('MCP_MODE') == '1' or
            not sys.stdout.isatty() or  # 检测是否在管道或重定向环境中运行
            not sys.stdin.isatty()  # 检测标准输入是否被重定向
        )
        
        if config_path:
            self.config_path = Path(config_path)
        else:
            # 统一使用 ~/.remote-terminal 作为标准配置目录
            self.config_path = Path.home() / '.remote-terminal' / 'config.yaml'
        
        # 设置config_dir - 必须在ensure_directories()之前
        self.config_dir = self.config_path.parent
        # 模板目录应该在用户配置目录下，而不是项目目录
        self.templates_dir = self.config_dir / "templates"
        # 项目模板目录用于复制初始模板
        self.project_templates_dir = Path(__file__).parent / "templates"
        
        # 在创建目录之前，先检查是否需要迁移旧配置
        self.migrate_legacy_config()
        
        # 🛡️ 重要修复：只在需要时才创建目录和模板
        # 不在初始化时无条件创建，避免意外覆盖用户配置
        # self.ensure_directories()  # 移到需要时再调用
        
        # Docker配置现在统一在enhanced_config_manager中处理
        # 不再需要独立的docker_manager
        
    def migrate_legacy_config(self):
        """迁移旧的配置文件到新的标准位置"""
        legacy_config_dir = Path.home() / '.remote-terminal-mcp'
        legacy_config_file = legacy_config_dir / 'config.yaml'
        new_config_file = self.config_path
        
        # 如果新配置文件不存在，但旧配置文件存在，则进行迁移
        if not new_config_file.exists() and legacy_config_file.exists():
            try:
                # 确保新配置目录存在
                new_config_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 复制配置文件
                import shutil
                shutil.copy2(legacy_config_file, new_config_file)
                
                # 迁移其他相关文件
                legacy_docker_dir = legacy_config_dir / 'docker_configs'
                new_docker_dir = self.config_dir / 'docker_configs'
                if legacy_docker_dir.exists():
                    shutil.copytree(legacy_docker_dir, new_docker_dir, dirs_exist_ok=True)
                
                legacy_templates_dir = legacy_config_dir / 'templates'
                new_templates_dir = self.config_dir / 'templates'
                if legacy_templates_dir.exists():
                    shutil.copytree(legacy_templates_dir, new_templates_dir, dirs_exist_ok=True)
                
                legacy_docker_templates_dir = legacy_config_dir / 'docker_templates'
                new_docker_templates_dir = self.config_dir / 'docker_templates'
                if legacy_docker_templates_dir.exists():
                    shutil.copytree(legacy_docker_templates_dir, new_docker_templates_dir, dirs_exist_ok=True)
                
                if not self.is_mcp_mode:
                    self.colored_print("✅ 已成功迁移旧配置到新位置", Fore.GREEN)
                    self.colored_print(f"   从: {legacy_config_file}", Fore.CYAN)
                    self.colored_print(f"   到: {new_config_file}", Fore.CYAN)
                    
            except Exception as e:
                if not self.is_mcp_mode:
                    self.colored_print(f"❌ 配置迁移失败: {e}", Fore.RED)
    
    def has_user_config(self) -> bool:
        """检查是否存在用户配置（非模板配置）
        
        智能判断逻辑：
        1. 如果有非example-server的服务器，肯定是用户配置
        2. 如果只有example-server，检查其配置是否被修改过
        3. 如果配置文件有用户自定义的全局设置，也认为是用户配置
        4. 特殊保护：npm安装标记和最近修改时间（仅在不确定时作为保护机制）
        """
        try:
            # 如果配置文件不存在，肯定没有用户配置
            if not self.config_path.exists():
                return False
            
            # 尝试读取并解析配置文件
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 如果文件为空，没有用户配置
            if not content:
                return False
            
            # 尝试解析YAML
            try:
                config = yaml.safe_load(content)
                if not config or not isinstance(config, dict):
                    return False
            except yaml.YAMLError:
                # 如果YAML格式错误，认为没有有效用户配置
                return False
            
            # 检查是否有servers配置
            servers = config.get('servers', {})
            if not servers:
                return False
            
            # 1. 如果有非example-server的服务器，肯定是用户配置
            non_example_servers = [name for name in servers.keys() if name != 'example-server']
            if non_example_servers:
                if not self.is_mcp_mode:
                    self.colored_print(f"✅ 检测到用户服务器配置: {', '.join(non_example_servers)}", Fore.GREEN)
                return True
            
            # 2. 如果只有example-server，检查其配置是否被修改过
            if 'example-server' in servers:
                example_config = servers['example-server']
                
                # 检查关键字段是否被修改
                default_indicators = [
                    example_config.get('host') == 'example.com',
                    example_config.get('username') == 'your-username',
                    '示例服务器配置' in example_config.get('description', '')
                ]
                
                # 如果有任何关键字段被修改，认为是用户配置
                if not all(default_indicators):
                    if not self.is_mcp_mode:
                        self.colored_print("✅ 检测到example-server配置已被用户修改", Fore.GREEN)
                    return True
            
            # 3. 检查是否有用户自定义的全局设置
            global_settings = config.get('global_settings', {})
            if global_settings:
                # 检查是否有非默认的全局设置
                default_global = {
                    'default_timeout': 30,
                    'auto_recovery': True,
                    'log_level': 'INFO',
                    'default_shell': 'bash'
                }
                
                for key, value in global_settings.items():
                    if key not in default_global or default_global[key] != value:
                        if not self.is_mcp_mode:
                            self.colored_print(f"✅ 检测到用户自定义全局设置: {key}={value}", Fore.GREEN)
                        return True
            
            # 4. 特殊保护：检查文件修改时间
            try:
                import os
                import time
                file_mtime = os.path.getmtime(self.config_path)
                current_time = time.time()
                
                # 如果文件在过去24小时内被修改过，且不是刚刚创建的，认为可能有用户配置
                if current_time - file_mtime < 86400 and current_time - file_mtime > 60:
                    if not self.is_mcp_mode:
                        self.colored_print("✅ 检测到配置文件最近被修改，可能包含用户配置", Fore.YELLOW)
                    return True
                    
            except Exception:
                pass
            
            # 如果所有检查都通过，认为是默认配置
            return False
            
        except Exception as e:
            if not self.is_mcp_mode:
                self.colored_print(f"⚠️ 检查用户配置时出错: {e}", Fore.YELLOW)
            # 出错时保守处理，认为有用户配置以避免覆盖
            return True
    
    def colored_print(self, text: str, color=Fore.WHITE, style=""):
        """彩色打印 - 在MCP模式下禁止输出"""
        if self.is_mcp_mode:
            # 在MCP模式下，完全禁止输出以避免JSON格式错误
            return True
        else:
            print(f"{color}{style}{text}{Style.RESET_ALL}")
        return True
    
    def show_progress(self, current_step: int, total_steps: int, step_name: str):
        """显示进度指示器"""
        progress_bar = "█" * current_step + "░" * (total_steps - current_step)
        self.colored_print(f"\n📊 进度: [{progress_bar}] {current_step}/{total_steps}", Fore.CYAN)
        self.colored_print(f"当前步骤: {step_name}", Fore.YELLOW)
    
    def smart_input(self, prompt: str, validator=None, suggestions=None, default="", show_suggestions=True):
        """智能输入函数，支持验证和建议"""
        
        # 在MCP模式下，避免交互式输入
        if self.is_mcp_mode:
            if default:
                return default
            else:
                # 为MCP模式提供合理的默认值
                mcp_defaults = {
                    "服务器名称": "mcp-server",
                    "服务器地址": "localhost", 
                    "用户名": "user",
                    "SSH端口": "22",
                    "选择操作": "0",  # 退出
                    "选择连接方式": "1",  # SSH
                    "是否使用Docker容器": "n",
                    "是否启用文件同步功能": "n",
                    "容器名称": "dev-container",
                    "Docker镜像": "ubuntu:20.04",
                    "Shell环境": "bash",
                    "配置方式": "1",  # 快速配置
                    "选择配置方式": "1",
                    "选择Docker配置方式": "1"
                }
                # 从提示中匹配合适的默认值
                for key, value in mcp_defaults.items():
                    if key in prompt:
                        return value
                return ""  # 最后的默认值
        
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
    
    def _configure_server(self, server_type: str, ask_for_name: bool = True, enable_sync: bool = True) -> dict:
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
        
        # 同步功能配置 - 只在启用同步的情况下配置
        sync_config = None
        if enable_sync:
            sync_config = self._configure_sync(server_name)
        
        server_config = {
            "name": server_name,
            "host": server_host,
            "user": username,
            "port": port,
            "password": password
        }
        
        if sync_config:
            server_config["sync"] = sync_config
        
        return server_config
    
    def _configure_sync(self, server_name: str) -> Optional[Dict[str, Any]]:
        """配置同步功能"""
        self.colored_print(f"\n🔄 配置同步功能 (可选)", Fore.CYAN)
        self.colored_print("同步功能可以让您在本地VSCode中直接编辑远程文件", Fore.CYAN)
        
        # 询问是否启用同步
        enable_sync_input = self.smart_input("是否启用文件同步功能", 
                                           validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
                                           suggestions=['y (推荐)', 'n'],
                                           default='n')
        if not enable_sync_input or enable_sync_input.lower() in ['n', 'no']:
            self.colored_print("⏭️ 跳过同步配置", Fore.YELLOW)
            return None
        
        self.colored_print("✅ 启用同步功能", Fore.GREEN)
        
        # 调用详细配置方法
        return self._configure_sync_details(server_name)
    
    def _configure_relay_host(self, host_type: str, current_config: Dict, default_host: str = "", default_user: str = "") -> Optional[Dict[str, Any]]:
        """配置relay连接中的单个主机（跳板机或目标服务器）"""
        self.colored_print(f"配置{host_type}连接信息:", Fore.YELLOW)
        
        # 主机地址
        host = self.smart_input(f"{host_type}地址", 
                              default=current_config.get('host', default_host),
                              validator=self.validate_hostname)
        if not host:
            return None
        
        # 用户名
        username = self.smart_input(f"{host_type}用户名", 
                                  default=current_config.get('username', default_user),
                                  validator=self.validate_username)
        if not username:
            return None
        
        # 端口
        port = self.smart_input(f"{host_type}SSH端口", 
                              default=str(current_config.get('port', 22)),
                              validator=self.validate_port)
        if not port:
            return None
        
        # 密码配置
        self.colored_print(f"\n🔐 {host_type}认证配置", Fore.YELLOW)
        current_password = current_config.get('password', '')
        
        if current_password:
            # 显示当前密码的掩码版本
            masked_password = '*' * min(len(current_password), 8)
            self.colored_print(f"当前密码: {masked_password}", Fore.CYAN)
            password_prompt = f"{host_type}登录密码 (回车保持当前密码，输入新密码则更新)"
            default_password = current_password
        else:
            password_prompt = f"{host_type}登录密码 (直接回车表示使用SSH密钥认证)"
            default_password = ""
        
        password_input = self.smart_input(password_prompt, 
                                        default=default_password,
                                        show_suggestions=False)
        
        # 构建配置
        host_config = {
            "host": host,
            "username": username,
            "port": int(port)
        }
        
        # 处理密码配置
        if password_input and password_input.strip():
            host_config["password"] = password_input.strip()
            if password_input.strip() == current_password:
                self.colored_print(f"✅ {host_type}保持现有密码认证", Fore.GREEN)
            else:
                self.colored_print(f"✅ {host_type}已更新密码认证", Fore.GREEN)
        else:
            self.colored_print(f"✅ {host_type}将使用SSH密钥认证", Fore.GREEN)
        
        return host_config

    def _configure_sync_details(self, server_name: str, current_sync_config: Dict = None) -> Optional[Dict[str, Any]]:
        """配置同步功能详细设置（不再询问是否启用）"""
        self.colored_print("✅ 启用同步功能", Fore.GREEN)
        
        # 获取现有配置的默认值
        if current_sync_config is None:
            current_sync_config = {}
        
        # 配置远程工作目录
        current_remote = current_sync_config.get('remote_workspace', '/home/Code')
        remote_workspace = self.smart_input("远程工作目录", 
                                          validator=lambda x: bool(x and x.startswith('/')),
                                          default=current_remote,
                                          suggestions=["/home/Code", "/workspace", "/opt/workspace"])
        if not remote_workspace:
            return None
        
        # 配置本地工作目录
        current_local = current_sync_config.get('local_workspace', os.getcwd())
        current_dir = os.getcwd()
        
        if current_local != current_dir:
            self.colored_print(f"📁 当前本地目录: {current_dir}", Fore.CYAN)
            self.colored_print(f"📁 配置中的本地目录: {current_local}", Fore.YELLOW)
        else:
            self.colored_print(f"📁 当前本地目录: {current_dir}", Fore.CYAN)
        
        local_workspace = self.smart_input("本地工作目录", 
                                         default=current_local,
                                         show_suggestions=False)
        if not local_workspace:
            local_workspace = current_local
        
        # FTP配置
        self.colored_print("\n🌐 FTP服务器配置", Fore.CYAN)
        
        current_ftp_port = str(current_sync_config.get('ftp_port', 8021))
        ftp_port = self.smart_input("FTP端口", 
                                   validator=self.validate_port,
                                   default=current_ftp_port,
                                   show_suggestions=False)
        if not ftp_port:
            ftp_port = current_ftp_port
        
        current_ftp_user = current_sync_config.get('ftp_user', 'ftpuser')
        ftp_user = self.smart_input("FTP用户名", 
                                   default=current_ftp_user,
                                   show_suggestions=False)
        if not ftp_user:
            ftp_user = current_ftp_user
        
        current_ftp_password = current_sync_config.get('ftp_password', 'your_ftp_password')
        ftp_password = self.smart_input("FTP密码", 
                                       default=current_ftp_password,
                                       show_suggestions=False)
        if not ftp_password:
            ftp_password = current_ftp_password
        
        sync_config = {
            "enabled": True,
            "remote_workspace": remote_workspace,
            "local_workspace": local_workspace,
            "ftp_port": int(ftp_port),
            "ftp_user": ftp_user,
            "ftp_password": ftp_password
        }
        
        self.colored_print("✅ 同步配置完成", Fore.GREEN)
        self.colored_print(f"   远程目录: {remote_workspace}", Fore.GREEN)
        self.colored_print(f"   本地目录: {local_workspace}", Fore.GREEN)
        self.colored_print(f"   FTP端口: {ftp_port}", Fore.GREEN)
        
        return sync_config
    
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
        """确保必要的目录存在 - 超级保护版本"""
        self.config_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        
        # 创建docker_configs目录
        docker_configs_dir = self.config_dir / 'docker_configs'
        docker_configs_dir.mkdir(exist_ok=True)
        
        # 创建其他可能需要的目录
        scripts_dir = self.config_dir / 'scripts'
        scripts_dir.mkdir(exist_ok=True)
        
        # 🛡️ 重要修复：只在没有用户配置时才创建模板
        # 避免在有用户配置时意外触发覆盖逻辑
        if not self.config_path.exists() and not self.has_user_config():
            self.create_default_templates()

    def restore_npm_config_if_needed(self):
        """简化版本：移除复杂的NPM配置恢复逻辑"""
        # 简化版本：什么都不做
        pass
    
    def create_default_templates(self):
        """创建默认配置模板文件"""
        # 确保模板目录存在
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # 先尝试从项目模板目录复制现有模板
        if self.project_templates_dir.exists():
            import shutil
            for template_file in self.project_templates_dir.glob("*.yaml"):
                target_file = self.templates_dir / template_file.name
                if not target_file.exists():
                    try:
                        shutil.copy2(template_file, target_file)
                        if not self.is_mcp_mode:
                            self.colored_print(f"📄 复制模板: {template_file.name}", Fore.CYAN)
                    except Exception as e:
                        if not self.is_mcp_mode:
                            self.colored_print(f"⚠️ 复制模板失败 {template_file.name}: {e}", Fore.YELLOW)
        
        # 如果项目模板不存在或复制失败，创建基本模板
        templates = {
            "ssh_server.yaml": {
                "servers": {
                    "example-ssh": {
                        "host": "REPLACE_WITH_YOUR_SERVER_HOST",
                        "user": "REPLACE_WITH_YOUR_USERNAME",
                        "port": 22,
                        "type": "ssh",
                        "description": "Standard SSH server - TEMPLATE ONLY, REPLACE VALUES BEFORE USE"
                    }
                }
            },
            "relay_server.yaml": {
                "servers": {
                    "example-relay": {
                        "host": "REPLACE_WITH_TARGET_SERVER",
                        "user": "REPLACE_WITH_YOUR_USERNAME", 
                        "type": "relay",
                        "relay_command": "relay-cli -s REPLACE_WITH_TARGET_SERVER",
                        "description": "Server via relay-cli - TEMPLATE ONLY, REPLACE VALUES BEFORE USE"
                    }
                }
            },
            "docker_server.yaml": {
                "servers": {
                    "example-docker": {
                        "host": "REPLACE_WITH_DOCKER_HOST",
                        "user": "REPLACE_WITH_YOUR_USERNAME",
                        "type": "docker",
                        "container_name": "REPLACE_WITH_CONTAINER_NAME",
                        "docker_image": "ubuntu:20.04",
                        "auto_create_container": True,
                        "tmux_session": "REPLACE_WITH_SESSION_NAME",
                        "description": "Docker development environment - TEMPLATE ONLY, REPLACE VALUES BEFORE USE"
                    }
                }
            },
            "complex_server.yaml": {
                "servers": {
                    "example-complex": {
                        "host": "REPLACE_WITH_COMPLEX_SERVER",
                        "user": "REPLACE_WITH_YOUR_USERNAME",
                        "port": 2222,
                        "type": "relay",
                        "relay_command": "relay-cli -s REPLACE_WITH_COMPLEX_SERVER",
                        "container_name": "REPLACE_WITH_CONTAINER_NAME",
                        "docker_image": "pytorch/pytorch:latest",
                        "auto_create_container": True,
                        "tmux_session": "REPLACE_WITH_SESSION_NAME",
                        "environment": {
                            "CUDA_VISIBLE_DEVICES": "0,1",
                            "PYTHONPATH": "/workspace"
                        },
                        "post_connect_commands": [
                            "cd /workspace",
                            "source activate pytorch",
                            "echo 'Environment ready!'"
                        ],
                        "description": "Complex ML development environment - TEMPLATE ONLY, REPLACE VALUES BEFORE USE"
                    }
                }
            }
        }
        
        # 只创建不存在的模板文件
        for template_name, content in templates.items():
            template_path = self.templates_dir / template_name
            if not template_path.exists():
                try:
                    with open(template_path, 'w', encoding='utf-8') as f:
                        yaml.dump(content, f, default_flow_style=False, allow_unicode=True)
                    if not self.is_mcp_mode:
                        self.colored_print(f"📄 创建模板: {template_name}", Fore.GREEN)
                except Exception as e:
                    if not self.is_mcp_mode:
                        self.colored_print(f"❌ 创建模板失败 {template_name}: {e}", Fore.RED)
    
    def main_menu(self):
        """主菜单 - 简化版"""
        
        # 在MCP模式下，不运行交互式菜单
        if self.is_mcp_mode:
            self.colored_print("MCP模式下无法运行交互式主菜单", Fore.YELLOW)
            return False
        
        self.colored_print("\n🚀 Remote Terminal Configuration Manager", Fore.CYAN, Style.BRIGHT)
        self.colored_print("=" * 50, Fore.CYAN)
        
        self.colored_print("\n📋 配置选项:", Fore.GREEN, Style.BRIGHT)
        self.colored_print("  1. 向导配置 (Guided Setup) - 推荐使用", Fore.GREEN)
        self.colored_print("  2. 手动配置 (Manual Setup) - 直接编辑配置文件", Fore.BLUE)
        self.colored_print("  3. 🐳 创建docker容器环境配置", Fore.CYAN)
        
        self.colored_print("\n✏️ 编辑功能:", Fore.YELLOW, Style.BRIGHT)
        self.colored_print("  4. 📝 编辑服务器配置", Fore.YELLOW)
        self.colored_print("  5. 🐳 编辑Docker环境配置", Fore.YELLOW)
        
        self.colored_print("\n⚙️ 管理功能:", Fore.MAGENTA, Style.BRIGHT)
        self.colored_print("  6. 管理现有配置", Fore.MAGENTA)
        self.colored_print("  7. 测试连接", Fore.MAGENTA)
        self.colored_print("  0. 退出", Fore.WHITE)
        
        self.colored_print("=" * 50, Fore.CYAN)
        
        while True:
            choice = self.smart_input("\n请选择操作", 
                                    validator=lambda x: x in ['0', '1', '2', '3', '4', '5', '6', '7'],
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
                return self.edit_server_config()
            elif choice == "5":
                return self.edit_docker_config()
            elif choice == "6":
                return self.manage_existing()
            elif choice == "7":
                return self.test_connection()
            elif choice == "0":
                self.colored_print("👋 再见！", Fore.CYAN)
                return
            else:
                self.colored_print(f"{ConfigError.ERROR} 无效选择，请重新输入", Fore.RED)
    
    def quick_setup(self):
        """快速配置 - 改进版"""
        # 在MCP模式下，使用预设默认值快速创建配置
        if self.is_mcp_mode:
            try:
                # MCP模式：使用预设默认值创建一个示例服务器配置
                server_name = "mcp-server"
                server_host = "localhost"
                username = "user"
                
                config = {"servers": {server_name: {
                    "host": server_host,
                    "user": username,
                    "port": 22,
                    "type": "ssh", 
                    "description": f"Quick setup: {server_name} via SSH"
                }}}
                
                # 保存配置
                self.save_config(config)
                return True  # 成功返回
            except Exception as e:
                return False  # 失败返回
        
        self.colored_print("\n⚡ 快速配置模式", Fore.YELLOW, Style.BRIGHT)
        self.colored_print("只需回答几个关键问题，5分钟完成配置", Fore.YELLOW)
        self.colored_print("-" * 40, Fore.YELLOW)
        
        self.show_progress(1, 5, "收集基本信息")
        
        # 基本信息
        server_name = self.smart_input("服务器名称", 
                                     validator=lambda x: bool(x and len(x) > 0),
                                     suggestions=["gpu-server-1", "dev-server", "ml-server"])
        if not server_name:
            return False
            
        server_host = self.smart_input("服务器地址", 
                                     validator=self.validate_hostname,
                                     suggestions=["192.168.1.100", "server.example.com"])
        if not server_host:
            return False
            
        username = self.smart_input("用户名", 
                                   validator=self.validate_username,
                                   suggestions=["ubuntu", "root", os.getenv('USER', 'user')])
        if not username:
            return False
        
        self.show_progress(2, 5, "选择连接方式")
        
        # 连接方式
        self.colored_print("\n连接方式:", Fore.CYAN)
        self.colored_print("1. 直接SSH连接 (标准方式)", Fore.GREEN)
        self.colored_print("2. 通过relay-cli连接 (百度内网)", Fore.BLUE)
        
        connection_type = self.smart_input("选择连接方式", 
                                         validator=lambda x: x in ['1', '2'],
                                         suggestions=['1 (推荐)', '2 (内网)'])
        if not connection_type:
            return False
        
        self.show_progress(3, 5, "Docker配置")
        
        # 是否使用Docker
        use_docker_input = self.smart_input("是否使用Docker容器", 
                                           validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
                                           suggestions=['y (推荐)', 'n'],
                                           default='n')
        if not use_docker_input:
            return False
            
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
                return False
                
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
        return True
    
    def guided_setup(self):
        """向导配置 - 重新设计的配置体验"""
        
        # 在MCP模式下，不运行交互式配置
        if self.is_mcp_mode:
            self.colored_print("MCP模式下的配置向导已被调用，但无法进行交互式配置", Fore.YELLOW)
            return False
        
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
            
            # 先询问是否需要二级跳板机
            self.colored_print("\n🔗 连接架构选择:", Fore.YELLOW)
            self.colored_print("1. 单级跳板: relay-cli → 目标服务器", Fore.GREEN)
            self.colored_print("2. 二级跳板: relay-cli → 中继服务器 → 目标服务器", Fore.BLUE)
            
            jump_type = self.smart_input("选择连接架构", 
                                       validator=lambda x: x in ['1', '2'],
                                       default='1',
                                       show_suggestions=False)
            if not jump_type:
                return
            
            # 配置服务器名称
            server_name = self.smart_input("🏷️ 服务器配置名称", 
                                         validator=lambda x: bool(x and len(x) > 0),
                                         show_suggestions=False)
            if not server_name:
                return
            
            if jump_type == "2":
                # 二级跳板：先配置第一级跳板机（relay-cli直接连接的服务器）
                self.colored_print("\n🏃 配置第一级跳板机", Fore.MAGENTA)
                self.colored_print("💡 连接流程: 本地 → relay-cli → 第一级跳板机 → 最终目标服务器", Fore.YELLOW)
                
                first_jump_server = self._configure_server("第一级跳板机", ask_for_name=False, enable_sync=False)
                if not first_jump_server:
                    return
                
                # 然后配置最终目标服务器
                self.colored_print("\n🎯 配置最终目标服务器", Fore.CYAN)
                final_target_server = self._configure_server("最终目标服务器", ask_for_name=False, enable_sync=False)
                if not final_target_server:
                    return
                
                # 生成二级跳板配置
                config = {"servers": {server_name: {
                    "host": first_jump_server["host"],  # relay-cli连接到第一级跳板机
                    "username": first_jump_server["user"],
                    "port": int(first_jump_server.get("port", 22)),
                    "private_key_path": "~/.ssh/id_rsa",
                    "type": "script_based",
                    "connection_type": "relay",
                    "description": f"Relay二级跳板: {server_name}",
                    "session": {
                        "name": f"{server_name}_session",
                        "shell": "/bin/bash",
                        "working_directory": "~"
                    },
                    "specs": {
                        "connection": {
                            "tool": "relay-cli",
                            "target": {"host": first_jump_server["host"]},  # relay-cli连接的第一级跳板机
                            "jump_host": {  # 第一级跳板机再连接到的最终目标
                                "host": final_target_server["host"],
                                "username": final_target_server["user"]
                            }
                        }
                    }
                }}}
                
                # 添加密码配置
                if first_jump_server.get("password"):
                    config["servers"][server_name]["password"] = first_jump_server["password"]
                if final_target_server.get("password"):
                    config["servers"][server_name]["specs"]["connection"]["jump_host"]["password"] = final_target_server["password"]
                    
            else:
                # 单级跳板：只需要配置一个目标服务器
                self.colored_print("\n🎯 配置目标服务器", Fore.CYAN)
                self.colored_print("💡 连接流程: 本地 → relay-cli → 目标服务器", Fore.YELLOW)
                target_server = self._configure_server("目标服务器", ask_for_name=False, enable_sync=True)
                if not target_server:
                    return
                
                # 生成单级跳板配置
                config = {"servers": {server_name: {
                    "host": target_server["host"],
                    "username": target_server["user"],
                    "port": int(target_server.get("port", 22)),
                    "private_key_path": "~/.ssh/id_rsa",
                    "type": "script_based",
                    "connection_type": "relay",
                    "description": f"Relay单级跳板: {server_name}",
                    "session": {
                        "name": f"{server_name}_session",
                        "shell": "/bin/bash",
                        "working_directory": "~"
                    },
                    "specs": {
                        "connection": {
                            "tool": "relay-cli",
                            "target": {"host": target_server["host"]}
                        }
                    }
                }}}
                
                # 添加密码配置
                if target_server.get("password"):
                    config["servers"][server_name]["password"] = target_server["password"]
        
        else:
            # SSH直连 - 只需配置目标服务器
            self.colored_print("\n🖥️ 第2步：配置目标服务器", Fore.CYAN, Style.BRIGHT)
            server_config = self._configure_server("目标服务器")
            if not server_config:
                return
                
            config = {"servers": {server_config["name"]: {
                "host": server_config["host"],
                "username": server_config["user"],
                "port": int(server_config.get("port", 22)),
                "private_key_path": "~/.ssh/id_rsa",
                "type": "script_based",
                "connection_type": "ssh",
                "description": f"SSH直连: {server_config['name']}",
                "session": {
                    "name": f"{server_config['name']}_session",
                    "shell": "/bin/bash",
                    "working_directory": "~"
                },
                "specs": {
                    "connection": {
                        "type": "ssh",
                        "timeout": 30
                    },
                    "environment_setup": {
                        "shell": "bash",
                        "working_directory": f"/home/{server_config['user']}"
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
                                           validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
                                           default='n')
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
          - "echo 'Environment ready!'"
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
                    self.save_config(config, merge_mode=False)  # 使用覆盖模式确保删除生效
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
        """保存配置 - 支持合并模式和覆盖模式"""
        try:
            if merge_mode:
                # 合并模式：读取现有配置并合并（用于添加新配置）
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
                
                final_config = existing_config
            else:
                # 覆盖模式：直接使用传入的配置（用于删除操作）
                final_config = config
            
            # 创建备份
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.backup_{int(__import__('time').time())}"
                import shutil
                shutil.copy2(self.config_path, backup_path)
                if not self.is_mcp_mode:
                    self.colored_print(f"📋 已创建配置备份: {backup_path}", Fore.CYAN)
            
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 原子性保存：先写临时文件，再重命名
            temp_path = f"{self.config_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                yaml.dump(final_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
                f.flush()
                os.fsync(f.fileno())
            
            # 原子性重命名
            os.rename(temp_path, self.config_path)
            
            if not self.is_mcp_mode:
                self.colored_print(f"✅ 配置已保存到: {self.config_path}", Fore.GREEN)
                
        except Exception as e:
            # 清理临时文件
            temp_path = f"{self.config_path}.tmp"
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if not self.is_mcp_mode:
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
        """获取现有服务器配置 - 智能配置管理"""
        try:
            # 确保配置文件存在，如果不存在则创建默认配置
            self.ensure_config_exists()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            return config.get('servers', {}) if config else {}
        except Exception:
            # 如果仍然出错，尝试重新创建配置文件
            try:
                self.create_default_config_template()
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                return config.get('servers', {}) if config else {}
            except Exception:
                return {}
    
    def get_existing_docker_configs(self) -> dict:
        """获取现有Docker配置 - 智能配置管理"""
        try:
            # 确保配置文件存在，如果不存在则创建默认配置
            self.ensure_config_exists()
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
            
            if not config or 'servers' not in config:
                return {}
            
            docker_configs = {}
            for server_name, server_config in config['servers'].items():
                if 'docker' in server_config:
                    docker_configs[server_config['docker'].get('container_name', server_name)] = server_config['docker']
            
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
        self.show_progress(1, 4, "基本容器信息")
        
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
        
        # 步骤2: Shell环境配置
        self.show_progress(2, 4, "Shell环境配置")
        
        self.colored_print("\n🐚 Shell环境配置", Fore.BLUE)
        self.colored_print("💡 选择你的Shell环境，配置文件将从.remote-terminal目录复制", Fore.YELLOW)
        
        # 显示Shell选项
        self.colored_print("\n📋 可选Shell类型:", Fore.CYAN)
        self.colored_print("  1. Bash (默认) - 简单可靠", Fore.WHITE)
        self.colored_print("  2. Zsh - 功能强大，支持主题和插件", Fore.WHITE)
        
        shell_options = {
            '1': {'name': 'bash', 'path': '/bin/bash', 'config_file': '.bashrc', 'config_dir': 'bash'},
            '2': {'name': 'zsh', 'path': '/bin/zsh', 'config_file': '.zshrc', 'config_dir': 'zsh'}
        }
        
        # Shell类型选择
        shell_type = self.smart_input("选择Shell类型", 
                                    validator=lambda x: x in ['1', '2'],
                                    suggestions=['1', '2'],
                                    default='1')
        if not shell_type:
            return False
        
        selected_shell = shell_options[shell_type]
        
        # 检查配置文件是否存在 (优先级: 用户配置 > 项目模板)
        user_config_dir = Path.home() / '.remote-terminal' / 'configs' / selected_shell['config_dir']
        project_template_dir = Path.cwd() / 'templates' / 'configs' / selected_shell['config_dir']
        
        config_source = None
        config_files = []
        
        # 优先检查用户配置目录
        if user_config_dir.exists():
            config_files = list(user_config_dir.glob('*'))
            if config_files:
                config_source = user_config_dir
                self.colored_print(f"\n📁 使用用户配置: {user_config_dir}", Fore.GREEN)
        
        # 如果用户配置不存在，检查项目模板
        if not config_files and project_template_dir.exists():
            config_files = list(project_template_dir.glob('*'))
            if config_files:
                config_source = project_template_dir
                self.colored_print(f"\n📁 使用项目模板: {project_template_dir}", Fore.CYAN)
        
        # 显示找到的配置文件
        if config_files:
            self.colored_print("✅ 发现以下配置文件:", Fore.GREEN)
            for file in config_files:
                self.colored_print(f"  • {file.name}", Fore.WHITE)
        else:
            self.colored_print("\nℹ️ 未找到配置文件，将使用系统默认配置", Fore.BLUE)
            self.colored_print(f"💡 提示: 你可以将配置文件放在以下位置:", Fore.YELLOW)
            self.colored_print(f"  • 用户配置: {user_config_dir}", Fore.WHITE)
            self.colored_print(f"  • 项目模板: {project_template_dir}", Fore.WHITE)
        
        # 步骤3: 配置选择
        self.show_progress(3, 4, "配置选择")
        
        self.colored_print("\n⚙️ 配置方式选择", Fore.CYAN)
        self.colored_print("  1. 快速配置 - 使用预设的常用配置", Fore.GREEN)
        self.colored_print("  2. 自定义配置 - 手动配置端口映射和挂载目录", Fore.YELLOW)
        
        config_mode = self.smart_input("选择配置方式", 
                                     validator=lambda x: x in ['1', '2'],
                                     suggestions=['1', '2'],
                                     default='1')
        
        if config_mode == "1":
            # 快速配置：使用预设
            ports = ["8080:8080", "8888:8888", "6006:6006"]  # 常用端口：web服务、jupyter、tensorboard
            volumes = ["/home:/home", "/data:/data"]  # 常用挂载目录
            self.colored_print("\n✅ 使用快速配置", Fore.GREEN)
            self.colored_print(f"端口映射: {', '.join(ports)}", Fore.WHITE)
            self.colored_print(f"目录挂载: {', '.join(volumes)}", Fore.WHITE)
        else:
            # 自定义配置
            self.show_progress(4, 5, "自定义配置")
            self.colored_print("\n🔧 自定义配置", Fore.YELLOW)
            
            # 端口映射配置
            self.colored_print("\n📡 端口映射配置 (格式: host:container，多个用逗号分隔)")
            ports_input = self.smart_input(
                "端口映射 (直接回车使用默认)",
                default="8080:8080,8888:8888,6006:6006",
                suggestions=["8080:8080,8888:8888,6006:6006", "3000:3000", "直接回车使用默认"]
            )
            ports = [p.strip() for p in ports_input.split(",") if p.strip()] if ports_input else []
            
            # 挂载目录配置
            self.colored_print("\n📁 挂载目录配置 (格式: host:container，多个用逗号分隔)")
            volumes_input = self.smart_input(
                "挂载目录 (直接回车使用默认)",
                default="/home:/home,/data:/data",
                suggestions=["/home:/home,/data:/data", "/workspace:/workspace", "直接回车使用默认"]
            )
            volumes = [v.strip() for v in volumes_input.split(",") if v.strip()] if volumes_input else []
        
        # 步骤4: 生成配置
        final_step = 4 if config_mode == "1" else 5
        self.show_progress(final_step, final_step, "生成Docker配置")
        
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
            "setup_commands": [],
            "shell_config": {
                "type": selected_shell['name'],
                "path": selected_shell['path'],
                "config_file": selected_shell['config_file']
            }
        }
        
        # 添加基础开发工具
        docker_config["setup_commands"].extend([
            "apt-get update",
            "apt-get install -y curl git vim wget"
        ])
        
        # 添加Shell相关的安装命令
        if selected_shell['name'] == 'zsh':
            docker_config["setup_commands"].extend([
                "apt-get install -y zsh",
                "chsh -s /bin/zsh"
            ])
        
        # 添加配置文件复制命令
        if config_source and config_files:
            # 添加配置文件复制命令
            docker_config["setup_commands"].append("# 复制Shell配置文件")
            for config_file in config_files:
                docker_config["setup_commands"].append(f"cp /host-configs/{selected_shell['config_dir']}/{config_file.name} ~/")
            
            # 添加配置目录挂载
            if "volumes" not in docker_config:
                docker_config["volumes"] = []
            docker_config["volumes"].append(f"{config_source}:/host-configs/{selected_shell['config_dir']}:ro")
            
            # 记录配置文件信息
            docker_config["shell_config"]["custom_configs"] = [f.name for f in config_files]
            docker_config["shell_config"]["config_source"] = str(config_source)
        else:
            # 使用默认配置
            docker_config["shell_config"]["custom_configs"] = []
            docker_config["shell_config"]["config_source"] = "system_default"
            if selected_shell['name'] == 'zsh':
                docker_config["setup_commands"].append("# 使用默认zsh配置")
        

        
        # 显示配置预览
        self.colored_print("\n✅ Docker配置生成完成！", Fore.GREEN, Style.BRIGHT)
        self.colored_print("=" * 50, Fore.GREEN)
        self.colored_print(f"容器名称: {container_name}", Fore.WHITE)
        self.colored_print(f"镜像: {docker_image}", Fore.WHITE)
        self.colored_print(f"Shell环境: {selected_shell['name']} ({selected_shell['path']})", Fore.WHITE)
        if docker_config["shell_config"]["custom_configs"]:
            self.colored_print(f"自定义配置: {', '.join(docker_config['shell_config']['custom_configs'])}", Fore.WHITE)
            config_source_type = "用户配置" if "/.remote-terminal/" in docker_config["shell_config"]["config_source"] else "项目模板"
            self.colored_print(f"配置来源: {config_source_type}", Fore.WHITE)
        else:
            self.colored_print("配置文件: 使用系统默认配置", Fore.WHITE)
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
                 "shell": docker_config["shell_config"]["path"]
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
        
        # 构建docker run命令 - 使用更完整的系统级配置
        cmd_parts = ["docker run"]
        
        # 系统级权限和安全配置
        cmd_parts.append("--privileged")
        cmd_parts.append(f"--name={docker_config['container_name']}")
        cmd_parts.append("--ulimit core=-1")
        cmd_parts.append("--security-opt seccomp=unconfined")
        cmd_parts.append("-dti")
        
        # 网络和系统命名空间配置
        cmd_parts.append("--net=host")
        cmd_parts.append("--uts=host") 
        cmd_parts.append("--ipc=host")
        cmd_parts.append("--security-opt=seccomp=unconfined")
        
        # 目录挂载 - 包含常用数据目录
        default_volumes = ["/home:/home", "/data1:/data1", "/data2:/data2", "/data3:/data3", "/data4:/data4"]
        volumes = docker_config.get('volumes', [])
        
        # 合并默认挂载和用户自定义挂载
        all_volumes = default_volumes.copy()
        for volume in volumes:
            if volume not in all_volumes:
                all_volumes.append(volume)
        
        for volume in all_volumes:
            cmd_parts.append(f"-v {volume}")
        
        # 共享内存配置
        cmd_parts.append("--shm-size=256g")
        
        # 重启策略
        cmd_parts.append("--restart=always")
        
        # 端口映射（如果使用host网络，端口映射会被忽略，但保留以供参考）
        if docker_config.get('ports'):
            self.colored_print("\n⚠️  注意：使用 --net=host 时，端口映射会被忽略", Fore.YELLOW)
            self.colored_print("以下端口配置仅供参考：", Fore.YELLOW)
            for port in docker_config.get('ports', []):
                self.colored_print(f"  - {port}", Fore.WHITE)
        
        # 环境变量
        for key, value in docker_config.get('environment', {}).items():
            cmd_parts.append(f"-e {key}={value}")
        
        # 工作目录
        if docker_config.get('working_directory'):
            cmd_parts.append(f"-w {docker_config['working_directory']}")
        
        # 镜像
        cmd_parts.append(docker_config['image'])
        
        # 显示命令
        docker_command = " \\\n  ".join(cmd_parts)
        self.colored_print(docker_command, Fore.WHITE)
        
        # 显示配置说明
        self.colored_print(f"\n📋 配置说明:", Fore.GREEN)
        self.colored_print("  • --privileged: 容器获得完整系统权限", Fore.WHITE)
        self.colored_print("  • --net=host: 使用主机网络栈", Fore.WHITE)
        self.colored_print("  • --uts=host: 共享主机UTS命名空间", Fore.WHITE)
        self.colored_print("  • --ipc=host: 共享主机IPC命名空间", Fore.WHITE)
        self.colored_print("  • --shm-size=256g: 设置共享内存大小", Fore.WHITE)
        self.colored_print("  • --ulimit core=-1: 不限制core dump大小", Fore.WHITE)
        self.colored_print("  • --security-opt seccomp=unconfined: 禁用seccomp安全限制", Fore.WHITE)
        self.colored_print("  • --restart=always: 容器自动重启", Fore.WHITE)
        
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
        docker_configs = self.get_existing_docker_configs()
        if not docker_configs:
            self.colored_print("❌ 没有找到Docker配置，请先创建Docker环境", Fore.RED)
            return
        
        self.colored_print("📋 可用的Docker环境:", Fore.GREEN)
        config_names = list(docker_configs.keys())
        for i, config_name in enumerate(config_names, 1):
            self.colored_print(f"  {i}. {config_name}", Fore.WHITE)
        
        # 选择Docker配置
        while True:
            try:
                choice = int(self.smart_input(f"选择Docker环境 (1-{len(config_names)})", 
                                            validator=lambda x: x.isdigit() and 1 <= int(x) <= len(config_names)))
                selected_docker = config_names[int(choice) - 1]
                break
            except (ValueError, IndexError):
                self.colored_print("❌ 无效选择", Fore.RED)
        
        # 获取Docker配置详情
        docker_config = docker_configs[selected_docker]
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
    
    def create_server_with_docker(self, docker_config: dict):
        """创建包含Docker的新服务器配置"""
        self.colored_print("\n🚀 创建包含Docker的服务器配置", Fore.GREEN, Style.BRIGHT)
        self.colored_print("-" * 40, Fore.GREEN)
        
        # 基本服务器信息
        server_name = self.smart_input("服务器名称", 
                                     validator=lambda x: bool(x and len(x) > 0),
                                     suggestions=[f"{docker_config.get('container_name', 'container')}_server", "docker_server"])
        
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
            "description": f"服务器配置与Docker环境: {docker_config.get('container_name', 'container')}",
            "specs": {
                "connection": {
                    "tool": "ssh",
                    "target": {"host": server_host}
                },
                "docker": docker_config
            },
            "session": {
                "name": f"{server_name}_session",
                "working_directory": docker_config.get("working_directory", "/workspace"),
                "shell": "/bin/bash"
            }
        }}}
        
        # 保存配置
        self.save_config(config)
        self.colored_print(f"\n✅ 服务器配置 '{server_name}' 创建成功！", Fore.GREEN, Style.BRIGHT)
        self.colored_print(f"已集成Docker环境: {docker_config.get('container_name', 'container')}", Fore.GREEN)
    
    def add_docker_to_existing_server(self, docker_config: dict):
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
        
        # 查找Docker模板
        templates_dir = self.config_dir / "docker_templates"
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
        self.colored_print("💡 使用统一的Docker向导配置...", Fore.CYAN)
        
        # 使用统一的Docker向导配置，强制选择自定义配置模式
        if self.docker_wizard_setup(called_from_guided_setup=True):
            # 获取最新创建的配置
            docker_configs = self.get_existing_docker_configs()
            if docker_configs:
                latest_config_name = list(docker_configs.keys())[-1]
                return docker_configs[latest_config_name]
        
        return {}
    
    def existing_docker_config(self, server_name: str) -> dict:
        """选择现有Docker配置"""
        self.colored_print("\n📂 选择现有Docker配置", Fore.MAGENTA, Style.BRIGHT)
        
        docker_configs = self.get_existing_docker_configs()
        if not docker_configs:
            self.colored_print("❌ 没有找到Docker配置，请先创建", Fore.RED)
            return {}
        
        self.colored_print("现有Docker配置:", Fore.CYAN)
        config_names = list(docker_configs.keys())
        for i, config_name in enumerate(config_names, 1):
            self.colored_print(f"  {i}. {config_name}", Fore.WHITE)
        
        while True:
            try:
                choice = int(self.smart_input(f"选择配置 (1-{len(config_names)})", 
                                            validator=lambda x: x.isdigit() and 1 <= int(x) <= len(config_names)))
                selected_config = config_names[int(choice) - 1]
                break
            except (ValueError, IndexError):
                self.colored_print("❌ 无效选择", Fore.RED)
        
        docker_config = docker_configs[selected_config]
        if docker_config:
            return docker_config
        
        return {}

    def edit_server_config(self, server_name: str = None):
        """编辑现有服务器配置"""
        # 在MCP模式下，不运行交互式编辑
        if self.is_mcp_mode:
            return True  # 直接返回成功，避免交互式操作
        
        self.colored_print("\n📝 编辑服务器配置", Fore.YELLOW, Style.BRIGHT)
        self.colored_print("=" * 50, Fore.YELLOW)
        
        # 获取现有服务器配置
        existing_servers = self.get_existing_servers()
        if not existing_servers:
            self.colored_print("❌ 没有找到现有的服务器配置", Fore.RED)
            self.colored_print("💡 请先使用向导配置创建服务器配置", Fore.YELLOW)
            return False
        
        # 如果指定了服务器名称，直接使用；否则让用户选择
        if server_name and server_name in existing_servers:
            selected_server = server_name
            self.colored_print(f"\n🎯 编辑指定服务器: {selected_server}", Fore.CYAN)
        else:
            # 显示现有服务器列表
            self.colored_print("\n📋 现有服务器配置:", Fore.CYAN)
            server_list = list(existing_servers.keys())
            for i, srv_name in enumerate(server_list, 1):
                server_info = existing_servers[srv_name]
                host = server_info.get('host', 'N/A')
                user = server_info.get('user', server_info.get('username', 'N/A'))
                conn_type = server_info.get('type', 'ssh')
                self.colored_print(f"  {i}. {srv_name} - {user}@{host} ({conn_type})", Fore.WHITE)
            
            # 选择要编辑的服务器
            choice = self.smart_input("选择要编辑的服务器 (输入序号)", 
                                    validator=lambda x: x.isdigit() and 1 <= int(x) <= len(server_list),
                                    suggestions=[str(i) for i in range(1, len(server_list) + 1)])
            if not choice:
                return
            
            selected_server = server_list[int(choice) - 1]
        current_config = existing_servers[selected_server]
        
        self.colored_print(f"\n✏️ 编辑服务器: {selected_server}", Fore.CYAN, Style.BRIGHT)
        self.colored_print("-" * 40, Fore.CYAN)
        
        # 显示当前配置并允许编辑
        self.colored_print("\n💡 当前配置如下，按回车保持不变，输入新值进行修改:", Fore.YELLOW)
        
        # 首先选择连接类型
        current_type = current_config.get('type', 'ssh')
        self.colored_print(f"\n当前连接类型: {current_type}", Fore.CYAN)
        self.colored_print("1. SSH直连", Fore.WHITE)
        self.colored_print("2. Relay跳板机连接", Fore.WHITE)
        
        type_choice = self.smart_input("连接类型", 
                                     default='1' if current_type == 'ssh' else '2',
                                     validator=lambda x: x in ['1', '2'])
        if type_choice is None:
            return
        
        new_type = 'ssh' if type_choice == '1' else 'script_based'
        
        # 初始化变量
        jump_host_config = None
        target_config = None
        
        # 根据连接类型配置不同的信息
        if new_type == 'ssh':
            # SSH直连配置
            self.colored_print("\n📡 SSH直连配置", Fore.CYAN, Style.BRIGHT)
            
            new_host = self.smart_input(f"服务器地址", 
                                      default=current_config.get('host', ''),
                                      validator=self.validate_hostname)
            if new_host is None:
                return
            
            new_user = self.smart_input(f"用户名", 
                                      default=current_config.get('user', current_config.get('username', '')),
                                      validator=self.validate_username)
            if new_user is None:
                return
            
            new_port = self.smart_input(f"端口", 
                                      default=str(current_config.get('port', 22)),
                                      validator=self.validate_port)
            if new_port is None:
                return
        
        else:
            # Relay跳板机连接配置
            self.colored_print("\n🔗 Relay跳板机连接配置", Fore.CYAN, Style.BRIGHT)
            
            # 获取当前的specs配置
            current_specs = current_config.get('specs', {}).get('connection', {})
            current_jump_host = current_specs.get('jump_host', {})
            current_target = current_specs.get('target', {})
            
            # 判断当前是单级跳板还是二级跳板
            is_two_level = bool(current_jump_host)
            
            self.colored_print("\n🔗 连接架构选择:", Fore.YELLOW)
            self.colored_print("1. 单级跳板: relay-cli → 目标服务器", Fore.GREEN)
            self.colored_print("2. 二级跳板: relay-cli → 第一级跳板机 → 最终目标服务器", Fore.BLUE)
            
            jump_type = self.smart_input("选择连接架构", 
                                       validator=lambda x: x in ['1', '2'],
                                       default='2' if is_two_level else '1',
                                       show_suggestions=False)
            if not jump_type:
                return
            
            if jump_type == "2":
                # 二级跳板配置
                self.colored_print("\n💡 连接流程: 本地 → relay-cli → 第一级跳板机 → 最终目标服务器", Fore.YELLOW)
                
                # 配置第一级跳板机（relay-cli直接连接的服务器）
                self.colored_print("\n🏃 第一级跳板机配置", Fore.MAGENTA)
                first_jump_config = self._configure_relay_host(
                    "第一级跳板机", 
                    current_target,  # 在二级跳板中，target是第一级跳板机
                    default_host=current_config.get('host', ''),
                    default_user=current_config.get('user', current_config.get('username', ''))
                )
                if not first_jump_config:
                    self.colored_print("❌ 第一级跳板机配置失败", Fore.RED)
                    return
                
                # 配置最终目标服务器
                self.colored_print("\n🎯 最终目标服务器配置", Fore.CYAN)
                final_target_config = self._configure_relay_host(
                    "最终目标服务器",
                    current_jump_host,  # 在二级跳板中，jump_host是最终目标
                    default_host=current_jump_host.get('host', ''),
                    default_user=current_jump_host.get('username', 'root')
                )
                if not final_target_config:
                    self.colored_print("❌ 最终目标服务器配置失败", Fore.RED)
                    return
                
                # 对于二级跳板，主配置使用第一级跳板机信息
                new_host = first_jump_config['host']
                new_user = first_jump_config['username'] 
                new_port = first_jump_config.get('port', 22)
                
                # 设置specs配置
                jump_host_config = final_target_config  # jump_host是最终目标
                target_config = first_jump_config       # target是第一级跳板机
                
            else:
                # 单级跳板配置
                self.colored_print("\n💡 连接流程: 本地 → relay-cli → 目标服务器", Fore.YELLOW)
                
                # 只需要配置目标服务器
                self.colored_print("\n🎯 目标服务器配置", Fore.CYAN)
                target_config = self._configure_relay_host(
                    "目标服务器",
                    current_target,
                    default_host=current_config.get('host', ''),
                    default_user=current_config.get('user', current_config.get('username', ''))
                )
                if not target_config:
                    self.colored_print("❌ 目标服务器配置失败", Fore.RED)
                    return
                
                # 对于单级跳板，主配置使用目标服务器信息
                new_host = target_config['host']
                new_user = target_config['username']
                new_port = target_config.get('port', 22)
                
                # 单级跳板不需要jump_host
                jump_host_config = None
        
        # 构建新配置
        updated_config = {
            "host": new_host or current_config.get('host'),
            "user": new_user or current_config.get('user', current_config.get('username')),
            "port": int(new_port) if new_port else current_config.get('port', 22),
            "type": new_type,
            "description": current_config.get('description', f"编辑的配置: {selected_server}")
        }
        
        # 保留其他配置项，但排除主配置中的password字段（因为密码现在分别存储在jump_host和target中）
        for key, value in current_config.items():
            if key not in ['host', 'user', 'username', 'port', 'type', 'specs', 'password']:
                updated_config[key] = value
        
        # 如果是relay连接，添加relay相关配置
        if new_type == 'script_based':
            updated_config['connection_type'] = 'relay'
            # 构建specs配置
            if jump_host_config:
                # 二级跳板配置
                updated_config['specs'] = {
                    "connection": {
                        "tool": "relay-cli",
                        "target": target_config,      # 第一级跳板机
                        "jump_host": jump_host_config  # 最终目标服务器
                    }
                }
            else:
                # 单级跳板配置
                updated_config['specs'] = {
                    "connection": {
                        "tool": "relay-cli",
                        "target": target_config  # 直接目标服务器
                    }
                }
        
        # 询问是否配置同步功能
        self.colored_print("\n🔄 文件同步功能配置", Fore.CYAN, Style.BRIGHT)
        current_sync = current_config.get('sync', {})
        has_sync = bool(current_sync.get('enabled', False))
        
        self.colored_print(f"当前同步状态: {'已启用' if has_sync else '未启用'}", Fore.YELLOW)
        self.colored_print("💡 文件同步功能可以让您在本地VSCode中直接编辑远程服务器文件", Fore.YELLOW)
        
        configure_sync = self.smart_input("是否启用文件同步功能 (y/n)", 
                                        validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
                                        default='y' if has_sync else 'n')
        
        if configure_sync and configure_sync.lower() in ['y', 'yes']:
            sync_config = self._configure_sync_details(selected_server, current_sync)
            if sync_config:
                updated_config['sync'] = sync_config
                self.colored_print("✅ 同步功能配置完成", Fore.GREEN)
            else:
                self.colored_print("⚠️ 同步功能配置跳过", Fore.YELLOW)
        elif has_sync:
            # 如果之前有同步配置但用户选择不配置，询问是否保留
            keep_sync = self.smart_input("是否保留现有同步配置 (y/n)", 
                                       validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
                                       default='y')
            if keep_sync and keep_sync.lower() in ['y', 'yes']:
                updated_config['sync'] = current_sync
                self.colored_print("✅ 保留现有同步配置", Fore.GREEN)
            else:
                self.colored_print("⚠️ 已移除同步配置", Fore.YELLOW)
        
        # 询问是否配置Docker环境
        self.colored_print("\n🐳 Docker环境配置", Fore.CYAN, Style.BRIGHT)
        current_docker = current_config.get('docker', {})
        has_docker = bool(current_docker.get('enabled', False))
        
        self.colored_print(f"当前Docker状态: {'已启用' if has_docker else '未启用'}", Fore.YELLOW)
        self.colored_print("💡 Docker环境可以让您自动进入指定的容器进行开发", Fore.YELLOW)
        
        configure_docker = self.smart_input("是否启用Docker环境 (y/n)", 
                                          validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
                                          default='y' if has_docker else 'n')
        
        if configure_docker and configure_docker.lower() in ['y', 'yes']:
            docker_config = self._configure_docker_for_server(selected_server, current_docker)
            if docker_config:
                updated_config['docker'] = docker_config
                self.colored_print("✅ Docker环境配置完成", Fore.GREEN)
            else:
                self.colored_print("⚠️ Docker环境配置跳过", Fore.YELLOW)
        elif has_docker:
            # 如果之前有Docker配置但用户选择不配置，询问是否保留
            keep_docker = self.smart_input("是否保留现有Docker配置 (y/n)", 
                                         validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
                                         default='y')
            if keep_docker and keep_docker.lower() in ['y', 'yes']:
                updated_config['docker'] = current_docker
                self.colored_print("✅ 保留现有Docker配置", Fore.GREEN)
            else:
                self.colored_print("⚠️ 已移除Docker配置", Fore.YELLOW)
        
        # 显示更新预览
        self.colored_print("\n📋 配置更新预览:", Fore.GREEN, Style.BRIGHT)
        self.colored_print(f"服务器名称: {selected_server}", Fore.WHITE)
        self.colored_print(f"地址: {updated_config['host']}", Fore.WHITE)
        self.colored_print(f"用户: {updated_config['user']}", Fore.WHITE)
        self.colored_print(f"端口: {updated_config['port']}", Fore.WHITE)
        self.colored_print(f"连接类型: {updated_config['type']}", Fore.WHITE)
        
        # 如果是relay连接，显示跳板机配置详情
        if updated_config.get('type') == 'script_based' and 'specs' in updated_config:
            specs = updated_config['specs']['connection']
            if 'jump_host' in specs and 'target' in specs:
                self.colored_print("\n🔗 Relay连接配置:", Fore.CYAN, Style.BRIGHT)
                
                jump_host = specs['jump_host']
                self.colored_print(f"  📍 跳板机: {jump_host['username']}@{jump_host['host']}:{jump_host.get('port', 22)}", Fore.WHITE)
                if 'password' in jump_host:
                    self.colored_print(f"    认证: 密码认证", Fore.GREEN)
                else:
                    self.colored_print(f"    认证: SSH密钥认证", Fore.YELLOW)
                
                target = specs['target']
                self.colored_print(f"  🎯 目标服务器: {target['username']}@{target['host']}:{target.get('port', 22)}", Fore.WHITE)
                if 'password' in target:
                    self.colored_print(f"    认证: 密码认证", Fore.GREEN)
                else:
                    self.colored_print(f"    认证: SSH密钥认证", Fore.YELLOW)
        
        # 显示同步配置预览
        if 'sync' in updated_config and updated_config['sync'].get('enabled'):
            sync_info = updated_config['sync']
            self.colored_print(f"同步功能: 已启用", Fore.GREEN)
            self.colored_print(f"  远程工作目录: {sync_info.get('remote_workspace', '/home/Code')}", Fore.WHITE)
            self.colored_print(f"  本地工作目录: {sync_info.get('local_workspace', '.')}", Fore.WHITE)
            self.colored_print(f"  FTP端口: {sync_info.get('ftp_port', 8021)}", Fore.WHITE)
        else:
            self.colored_print(f"同步功能: 未启用", Fore.YELLOW)
        
        # 显示Docker配置预览
        if 'docker' in updated_config and updated_config['docker'].get('enabled'):
            docker_info = updated_config['docker']
            self.colored_print(f"Docker环境: 已启用", Fore.GREEN)
            self.colored_print(f"  容器名称: {docker_info.get('container_name', 'N/A')}", Fore.WHITE)
            self.colored_print(f"  自动进入: {'是' if docker_info.get('auto_enter', False) else '否'}", Fore.WHITE)
            self.colored_print(f"  Shell类型: {docker_info.get('shell', 'bash')}", Fore.WHITE)
            self.colored_print(f"  工作目录: {docker_info.get('working_directory', '/workspace')}", Fore.WHITE)
        else:
            self.colored_print(f"Docker环境: 未启用", Fore.YELLOW)
        
        # 确认保存
        confirm = self.smart_input("确认保存更改 (y/n)", 
                                 validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
                                 default='y')
        if confirm and confirm.lower() in ['y', 'yes']:
            # 保存配置
            full_config = {"servers": {selected_server: updated_config}}
            self.save_config(full_config, merge_mode=True)
            self.colored_print(f"\n✅ 服务器配置已更新: {selected_server}", Fore.GREEN, Style.BRIGHT)
        else:
            self.colored_print("\n❌ 取消更新", Fore.YELLOW)

    def delete_server_config(self, server_name: str = None):
        """删除现有服务器配置"""
        self.colored_print("\n🗑️ 删除服务器配置", Fore.RED, Style.BRIGHT)
        self.colored_print("=" * 50, Fore.RED)
        
        # 获取现有服务器配置
        existing_servers = self.get_existing_servers()
        if not existing_servers:
            self.colored_print("❌ 没有找到现有的服务器配置", Fore.RED)
            self.colored_print("💡 没有可删除的服务器配置", Fore.YELLOW)
            return
        
        # 如果指定了服务器名称，直接使用；否则让用户选择
        if server_name and server_name in existing_servers:
            selected_server = server_name
            self.colored_print(f"\n🎯 删除指定服务器: {selected_server}", Fore.RED)
        else:
            # 显示现有服务器列表
            self.colored_print("\n📋 现有服务器配置:", Fore.CYAN)
            server_list = list(existing_servers.keys())
            for i, srv_name in enumerate(server_list, 1):
                server_info = existing_servers[srv_name]
                host = server_info.get('host', 'N/A')
                user = server_info.get('user', server_info.get('username', 'N/A'))
                conn_type = server_info.get('type', 'ssh')
                self.colored_print(f"  {i}. {srv_name} - {user}@{host} ({conn_type})", Fore.WHITE)
            
            # 选择要删除的服务器
            choice = self.smart_input("选择要删除的服务器 (输入序号)", 
                                    validator=lambda x: x.isdigit() and 1 <= int(x) <= len(server_list),
                                    suggestions=[str(i) for i in range(1, len(server_list) + 1)])
            if not choice:
                return
            
            selected_server = server_list[int(choice) - 1]
        
        current_config = existing_servers[selected_server]
        
        # 显示要删除的配置详情
        self.colored_print(f"\n⚠️ 即将删除服务器配置: {selected_server}", Fore.RED, Style.BRIGHT)
        self.colored_print("-" * 40, Fore.RED)
        self.colored_print(f"地址: {current_config.get('host', 'N/A')}", Fore.WHITE)
        self.colored_print(f"用户: {current_config.get('user', current_config.get('username', 'N/A'))}", Fore.WHITE)
        self.colored_print(f"端口: {current_config.get('port', 22)}", Fore.WHITE)
        self.colored_print(f"连接类型: {current_config.get('type', 'ssh')}", Fore.WHITE)
        
        # 检查是否有同步配置
        if 'sync' in current_config and current_config['sync'].get('enabled'):
            self.colored_print(f"同步功能: 已启用 (将一并删除)", Fore.YELLOW)
        
        # 警告信息
        self.colored_print("\n⚠️ 警告:", Fore.RED, Style.BRIGHT)
        self.colored_print("• 此操作不可逆", Fore.YELLOW)
        self.colored_print("• 将删除所有相关配置", Fore.YELLOW)
        self.colored_print("• 包括同步配置和其他自定义设置", Fore.YELLOW)
        
        # 二次确认
        self.colored_print(f"\n请输入服务器名称 '{selected_server}' 来确认删除:", Fore.RED)
        confirm_name = self.smart_input("确认服务器名称")
        
        if confirm_name != selected_server:
            self.colored_print("❌ 服务器名称不匹配，取消删除", Fore.YELLOW)
            return
        
        # 最终确认
        final_confirm = self.smart_input("最终确认删除 (输入 'DELETE' 确认)", 
                                       validator=lambda x: x == 'DELETE')
        
        if final_confirm == 'DELETE':
            try:
                # 读取当前配置文件
                if os.path.exists(self.config_path):
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                else:
                    config = {"servers": {}}
                
                # 删除指定服务器
                if 'servers' in config and selected_server in config['servers']:
                    del config['servers'][selected_server]
                    
                    # 保存更新后的配置
                    with open(self.config_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    
                    self.colored_print(f"\n✅ 服务器配置已删除: {selected_server}", Fore.GREEN, Style.BRIGHT)
                    self.colored_print("🔄 配置文件已更新", Fore.GREEN)
                else:
                    self.colored_print(f"❌ 未找到服务器配置: {selected_server}", Fore.RED)
                    
            except Exception as e:
                self.colored_print(f"❌ 删除配置时发生错误: {str(e)}", Fore.RED)
        else:
            self.colored_print("\n❌ 取消删除", Fore.YELLOW)

    def edit_docker_config(self):
        """编辑现有Docker配置"""
        self.colored_print("\n🐳 编辑Docker环境配置", Fore.YELLOW, Style.BRIGHT)
        self.colored_print("=" * 50, Fore.YELLOW)
        
        # 获取现有Docker配置
        existing_dockers = self.get_existing_docker_configs()
        if not existing_dockers:
            self.colored_print("❌ 没有找到现有的Docker配置", Fore.RED)
            self.colored_print("💡 请先使用Docker向导创建Docker配置", Fore.YELLOW)
            return
        
        # 显示现有Docker配置列表
        self.colored_print("\n📋 现有Docker配置:", Fore.CYAN)
        docker_list = list(existing_dockers.keys())
        for i, docker_name in enumerate(docker_list, 1):
            docker_info = existing_dockers[docker_name]
            image = docker_info.get('image', 'N/A')
            ports = docker_info.get('ports', [])
            port_str = ', '.join(ports) if ports else '无'
            self.colored_print(f"  {i}. {docker_name} - {image} [{port_str}]", Fore.WHITE)
        
        # 选择要编辑的Docker配置
        choice = self.smart_input("选择要编辑的Docker配置 (输入序号)", 
                                validator=lambda x: x.isdigit() and 1 <= int(x) <= len(docker_list),
                                suggestions=[str(i) for i in range(1, len(docker_list) + 1)])
        if not choice:
            return
        
        selected_docker = docker_list[int(choice) - 1]
        current_config = existing_dockers[selected_docker]
        
        self.colored_print(f"\n✏️ 编辑Docker配置: {selected_docker}", Fore.CYAN, Style.BRIGHT)
        self.colored_print("-" * 40, Fore.CYAN)
        
        # 显示当前配置并允许编辑
        self.colored_print("\n💡 当前配置如下，按回车保持不变，输入新值进行修改:", Fore.YELLOW)
        
        # 编辑基本信息
        new_image = self.smart_input("Docker镜像", 
                                   default=current_config.get('image', ''),
                                   suggestions=["ubuntu:20.04", "pytorch/pytorch:latest", "node:18-alpine"])
        if new_image is None:
            return
        
        # 保持现有端口映射配置（不提供编辑选项）
        new_ports = current_config.get('ports', [])
        
        # 编辑目录挂载
        current_volumes = current_config.get('volumes', [])
        current_volumes_str = ', '.join(current_volumes) if current_volumes else ''
        new_volumes_str = self.smart_input("目录挂载 (格式: /host:/container,/data:/data)", 
                                         default=current_volumes_str,
                                         suggestions=["/home:/home,/data:/data"])
        if new_volumes_str is None:
            return
        
        new_volumes = [v.strip() for v in new_volumes_str.split(',') if v.strip()] if new_volumes_str else []
        
        # 编辑Shell配置
        current_shell = current_config.get('shell_config', {}).get('type', 'bash')
        self.colored_print(f"\n当前Shell: {current_shell}", Fore.CYAN)
        self.colored_print("1. Bash", Fore.WHITE)
        self.colored_print("2. Zsh", Fore.WHITE)
        
        shell_choice = self.smart_input("Shell类型", 
                                      default='1' if current_shell == 'bash' else '2',
                                      validator=lambda x: x in ['1', '2'])
        if shell_choice is None:
            return
        
        new_shell = 'bash' if shell_choice == '1' else 'zsh'
        
        # 构建新配置
        updated_config = current_config.copy()
        updated_config.update({
            "image": new_image or current_config.get('image'),
            "ports": new_ports,
            "volumes": new_volumes,
            "shell_config": {
                "type": new_shell,
                "path": "/bin/bash" if new_shell == 'bash' else "/bin/zsh",
                "config_file": ".bashrc" if new_shell == 'bash' else ".zshrc"
            }
        })
        
        # 显示更新预览
        self.colored_print("\n📋 配置更新预览:", Fore.GREEN, Style.BRIGHT)
        self.colored_print(f"容器名称: {selected_docker}", Fore.WHITE)
        self.colored_print(f"镜像: {updated_config['image']}", Fore.WHITE)
        self.colored_print(f"Shell: {updated_config['shell_config']['type']}", Fore.WHITE)
        self.colored_print(f"端口映射: {', '.join(updated_config['ports']) if updated_config['ports'] else '无'}", Fore.WHITE)
        self.colored_print(f"目录挂载: {', '.join(updated_config['volumes']) if updated_config['volumes'] else '无'}", Fore.WHITE)
        
        # 确认保存
        confirm = self.smart_input("确认保存更改 (y/n)", 
                                 validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'],
                                 default='y')
        if confirm and confirm.lower() in ['y', 'yes']:
            # 保存Docker配置到模板目录
            self.save_docker_wizard_config(updated_config)
            
            # 同时更新主配置文件中使用该Docker配置的服务器
            self._update_servers_using_docker_config(selected_docker, updated_config)
            
            self.colored_print(f"\n✅ Docker配置已更新: {selected_docker}", Fore.GREEN, Style.BRIGHT)
        else:
            self.colored_print("\n❌ 取消更新", Fore.YELLOW)

    def _configure_docker_for_server(self, server_name: str, current_docker_config: Dict = None) -> Optional[Dict[str, Any]]:
        """为服务器配置Docker环境"""
        self.colored_print(f"\n🐳 配置 {server_name} 的Docker环境", Fore.CYAN, Style.BRIGHT)
        self.colored_print("-" * 40, Fore.CYAN)
        
        if current_docker_config is None:
            current_docker_config = {}
        
        # 检查是否有现有的Docker配置可以使用
        existing_dockers = self.get_existing_docker_configs()
        
        if existing_dockers:
            self.colored_print("\n💡 发现现有Docker配置，您可以:", Fore.YELLOW)
            self.colored_print("1. 使用现有Docker配置", Fore.WHITE)
            self.colored_print("2. 手动配置Docker容器", Fore.WHITE)
            
            choice = self.smart_input("选择配置方式", 
                                    validator=lambda x: x in ['1', '2'],
                                    default='1')
            
            if choice == '1':
                # 使用现有Docker配置
                self.colored_print("\n📋 现有Docker配置:", Fore.CYAN)
                docker_list = list(existing_dockers.keys())
                for i, docker_name in enumerate(docker_list, 1):
                    docker_info = existing_dockers[docker_name]
                    image = docker_info.get('image', 'N/A')
                    self.colored_print(f"  {i}. {docker_name} - {image}", Fore.WHITE)
                
                docker_choice = self.smart_input("选择Docker配置 (输入序号)", 
                                                validator=lambda x: x.isdigit() and 1 <= int(x) <= len(docker_list),
                                                suggestions=[str(i) for i in range(1, len(docker_list) + 1)])
                if not docker_choice:
                    return None
                
                selected_docker = docker_list[int(docker_choice) - 1]
                selected_config = existing_dockers[selected_docker]
                
                docker_config = {
                    "enabled": True,
                    "container_name": selected_config.get('container_name', selected_docker),
                    "image": selected_config.get('image', ''),
                    "auto_enter": True,
                    "shell": selected_config.get('shell_config', {}).get('type', 'bash'),
                    "working_directory": selected_config.get('working_directory', '/workspace')
                }
                
                # 立即保存到主配置文件
                self._save_docker_config_to_server(server_name, docker_config)
                return docker_config
        
        # 手动配置Docker容器
        self.colored_print("\n🔧 手动配置Docker容器", Fore.CYAN)
        
        # 容器名称
        default_container = current_docker_config.get('container_name', '')
        container_name = self.smart_input("Docker容器名称", 
                                         default=default_container,
                                         validator=self.validate_container_name)
        if not container_name:
            return None
        
        # 镜像名称（新增）
        default_image = current_docker_config.get('image', '')
        image_name = self.smart_input("Docker镜像名称", 
                                    default=default_image,
                                    suggestions=["ubuntu:20.04", "pytorch/pytorch:latest", "node:18-alpine"])
        if not image_name:
            return None
        
        # 是否自动进入容器
        default_auto_enter = current_docker_config.get('auto_enter', True)
        auto_enter_choice = self.smart_input("连接时自动进入容器 (y/n)", 
                                           default='y' if default_auto_enter else 'n',
                                           validator=lambda x: x.lower() in ['y', 'n', 'yes', 'no'])
        auto_enter = auto_enter_choice and auto_enter_choice.lower() in ['y', 'yes']
        
        # Shell类型
        default_shell = current_docker_config.get('shell', 'bash')
        self.colored_print(f"\n当前Shell: {default_shell}", Fore.CYAN)
        self.colored_print("1. Bash", Fore.WHITE)
        self.colored_print("2. Zsh", Fore.WHITE)
        
        shell_choice = self.smart_input("容器内Shell类型", 
                                      default='1' if default_shell == 'bash' else '2',
                                      validator=lambda x: x in ['1', '2'])
        shell_type = 'bash' if shell_choice == '1' else 'zsh'
        
        # 工作目录
        default_workdir = current_docker_config.get('working_directory', '/workspace')
        working_directory = self.smart_input("容器内工作目录", 
                                           default=default_workdir)
        
        docker_config = {
            "enabled": True,
            "container_name": container_name,
            "image": image_name,
            "auto_enter": auto_enter,
            "shell": shell_type,
            "working_directory": working_directory or '/workspace'
        }
        
        # 立即保存到主配置文件
        self._save_docker_config_to_server(server_name, docker_config)
        return docker_config
    
    def _save_docker_config_to_server(self, server_name: str, docker_config: Dict[str, Any]):
        """将Docker配置保存到服务器的主配置文件中"""
        try:
            # 读取现有配置
            existing_config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f) or {}
            
            # 确保servers节点存在
            if 'servers' not in existing_config:
                existing_config['servers'] = {}
            
            # 确保服务器配置存在
            if server_name not in existing_config['servers']:
                existing_config['servers'][server_name] = {}
            
            # 更新Docker配置
            existing_config['servers'][server_name]['docker'] = docker_config
            
            # 保存配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(existing_config, f, default_flow_style=False, allow_unicode=True)
            
            self.colored_print(f"✅ Docker配置已保存到服务器 {server_name}", Fore.GREEN)
            
        except Exception as e:
            self.colored_print(f"❌ 保存Docker配置失败: {e}", Fore.RED)
            raise
    
    def _update_servers_using_docker_config(self, docker_name: str, updated_config: Dict[str, Any]):
        """更新使用指定Docker配置的所有服务器"""
        try:
            # 读取现有配置
            existing_config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f) or {}
            
            if 'servers' not in existing_config:
                return
            
            updated_servers = []
            # 查找使用该Docker配置的服务器
            for server_name, server_config in existing_config['servers'].items():
                if 'docker' in server_config:
                    docker_config = server_config['docker']
                    if docker_config.get('container_name') == docker_name:
                        # 更新Docker配置
                        new_docker_config = {
                            "enabled": True,
                            "container_name": updated_config.get('container_name', docker_name),
                            "image": updated_config.get('image', ''),
                            "auto_enter": docker_config.get('auto_enter', True),
                            "shell": updated_config.get('shell_config', {}).get('type', 'bash'),
                            "working_directory": updated_config.get('working_directory', '/workspace')
                        }
                        existing_config['servers'][server_name]['docker'] = new_docker_config
                        updated_servers.append(server_name)
            
            if updated_servers:
                # 保存更新后的配置
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(existing_config, f, default_flow_style=False, allow_unicode=True)
                
                self.colored_print(f"✅ 已更新使用Docker配置 '{docker_name}' 的服务器: {', '.join(updated_servers)}", Fore.GREEN)
            
        except Exception as e:
            self.colored_print(f"❌ 更新服务器Docker配置失败: {e}", Fore.RED)

    def ensure_config_exists(self):
        """确保配置文件存在 - 超级保护版本
        
        保护策略：
        1. 优先检查：如果配置文件存在且有效，直接返回，绝不覆盖
        2. 智能检测：使用has_user_config检测是否有用户配置
        3. 多重保护：文件锁、备份检查、npm标记检查
        4. 只在真正的首次安装时创建配置
        5. 详细日志记录所有操作
        """
        import fcntl
        import tempfile
        import time
        
        try:
            # 🛡️ 第一道防线：如果配置文件存在，检查是否有效
            if self.config_path.exists():
                try:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    
                    # 如果文件不为空且包含基本结构，认为是有效用户配置
                    if content and ('servers:' in content or 'global_settings:' in content):
                        # 进一步检查是否为有效YAML
                        try:
                            import yaml
                            yaml.safe_load(content)
                            if not self.is_mcp_mode:
                                self.colored_print("✅ 配置文件已存在且有效，保护用户数据不被覆盖", Fore.GREEN)
                            return False
                        except yaml.YAMLError:
                            # YAML格式错误，需要重新创建
                            if not self.is_mcp_mode:
                                self.colored_print("⚠️ 配置文件格式错误，将重新创建", Fore.YELLOW)
                            # 备份损坏的文件
                            backup_path = self.config_path.parent / f'config.yaml.corrupted.{int(time.time())}'
                            try:
                                import shutil
                                shutil.copy2(self.config_path, backup_path)
                                if not self.is_mcp_mode:
                                    self.colored_print(f"📁 已备份损坏文件到: {backup_path}", Fore.CYAN)
                            except:
                                pass
                            # 删除损坏文件，继续创建新的
                            self.config_path.unlink()
                    else:
                        # 文件为空或不包含基本结构
                        if not self.is_mcp_mode:
                            self.colored_print("⚠️ 配置文件为空或格式不正确，将重新创建", Fore.YELLOW)
                        # 备份空文件
                        backup_path = self.config_path.parent / f'config.yaml.empty.{int(time.time())}'
                        try:
                            import shutil
                            shutil.copy2(self.config_path, backup_path)
                        except:
                            pass
                        # 删除空文件，继续创建新的
                        self.config_path.unlink()
                        
                except Exception as e:
                    if not self.is_mcp_mode:
                        self.colored_print(f"⚠️ 配置文件读取失败，将重新创建: {e}", Fore.YELLOW)
                    # 备份无法读取的文件
                    backup_path = self.config_path.parent / f'config.yaml.unreadable.{int(time.time())}'
                    try:
                        import shutil
                        shutil.copy2(self.config_path, backup_path)
                    except:
                        pass
                    # 删除无法读取的文件，继续创建新的
                    try:
                        self.config_path.unlink()
                    except:
                        pass
            
            # 🛡️ 第二道防线：检查是否有用户配置（通过备份等方式）
            if self.has_user_config():
                if not self.is_mcp_mode:
                    self.colored_print("✅ 检测到用户配置，保护不被覆盖", Fore.GREEN)
                return False
            
            # 🛡️ 第三道防线：检查npm更新场景
            npm_marker = self.config_path.parent / '.npm-installed'
            persistent_marker = Path.home() / '.remote-terminal-npm-installed'
            
            if npm_marker.exists() or persistent_marker.exists():
                # 检查是否真的有配置文件，如果没有就创建
                if not self.config_path.exists():
                    if not self.is_mcp_mode:
                        self.colored_print("⚠️ npm场景但配置文件不存在，创建默认配置", Fore.YELLOW)
                else:
                    if not self.is_mcp_mode:
                        self.colored_print("✅ 检测到npm包更新场景 - 保留现有配置", Fore.GREEN)
                    return False
            
            # 🛡️ 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用临时文件作为锁机制
            lock_file = self.config_path.parent / '.config_lock'
            
            try:
                # 尝试获取文件锁
                with open(lock_file, 'w') as lock_fd:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    
                    # 在锁保护下再次检查配置文件
                    if self.config_path.exists():
                        # 文件存在，检查是否为有效配置
                        try:
                            with open(self.config_path, 'r', encoding='utf-8') as f:
                                content = f.read().strip()
                            
                            # 如果文件不为空且包含基本结构，认为是有效用户配置
                            if content and ('servers:' in content or 'global_settings:' in content):
                                if not self.is_mcp_mode:
                                    self.colored_print("✅ 发现有效用户配置文件，保持不变", Fore.GREEN)
                                return False
                        except Exception as e:
                            if not self.is_mcp_mode:
                                self.colored_print(f"⚠️ 配置文件读取失败，重新创建: {e}", Fore.YELLOW)
                    
                    # 检查是否存在备份配置
                    backup_config = self.config_path.parent / 'config.yaml.backup'
                    persistent_backup = Path.home() / '.remote-terminal-config-backup.yaml'
                    
                    if backup_config.exists() or persistent_backup.exists():
                        if not self.is_mcp_mode:
                            self.colored_print("⚠️ 检测到备份配置，说明用户曾经有配置 - 不覆盖", Fore.YELLOW)
                        return False
                    
                    # 🛡️ 第四道防线：创建前再次确认文件不存在
                    if self.config_path.exists():
                        if not self.is_mcp_mode:
                            self.colored_print("⚠️ 配置文件在创建过程中突然出现，保护不覆盖", Fore.YELLOW)
                        return False
                    
                    # 只有在真正的首次安装时才创建
                    if not self.is_mcp_mode:
                        self.colored_print("📝 首次安装 - 创建新的配置文件...", Fore.CYAN)
                    
                    # 🛡️ 只在真正需要创建配置时才创建目录结构
                    self.ensure_directories()
                    self.create_default_config_template()
                    
                    # 🛡️ 创建后验证
                    if self.config_path.exists():
                        if not self.is_mcp_mode:
                            self.colored_print("✅ 默认配置文件创建成功", Fore.GREEN)
                        return True
                    else:
                        if not self.is_mcp_mode:
                            self.colored_print("❌ 配置文件创建失败", Fore.RED)
                        return False
                    
            except (IOError, OSError):
                # 无法获取锁，可能有其他进程在操作
                if not self.is_mcp_mode:
                    self.colored_print("⏳ 其他进程正在操作配置文件，等待...", Fore.YELLOW)
                
                # 等待一小段时间后重试
                import time
                time.sleep(0.1)
                
                # 简单检查文件是否存在 - 如果存在就不创建
                if self.config_path.exists():
                    if not self.is_mcp_mode:
                        self.colored_print("✅ 配置文件已存在，保持不变", Fore.GREEN)
                    return False
                else:
                    # 🛡️ 如果仍然不存在，先确保目录结构再尝试创建
                    self.ensure_directories()
                    self.create_default_config_template()
                    return True
            
            finally:
                # 清理锁文件
                try:
                    if lock_file.exists():
                        lock_file.unlink()
                except:
                    pass
                
        except Exception as e:
            # 如果出现任何错误，作为最后的保障
            if not self.is_mcp_mode:
                self.colored_print(f"❌ 配置文件处理失败: {e}", Fore.RED)
            
            # 只有在配置文件确实不存在且没有任何备份时才尝试创建
            if not self.config_path.exists():
                backup_config = self.config_path.parent / 'config.yaml.backup'
                persistent_backup = Path.home() / '.remote-terminal-config-backup.yaml'
                
                if backup_config.exists() or persistent_backup.exists():
                    if not self.is_mcp_mode:
                        self.colored_print("⚠️ 发现备份配置，不创建新配置", Fore.YELLOW)
                    return False
                
                try:
                    # 🛡️ 最后的保障：确保目录结构存在
                    self.ensure_directories()
                    self.create_default_config_template()
                    return True
                except Exception as create_error:
                    if not self.is_mcp_mode:
                        self.colored_print(f"❌ 创建默认配置失败: {create_error}", Fore.RED)
                    raise
            
            return False

    def create_default_config_template(self):
        """创建默认配置模板 - 超级安全版本
        
        安全策略：
        1. 检查文件是否已存在，如果存在则拒绝覆盖
        2. 只在文件真正不存在时才创建
        3. 添加详细日志以便调试
        """
        config_file = self.config_dir / 'config.yaml'
        
        # 安全检查：如果文件已存在，拒绝覆盖
        if config_file.exists():
            if not self.is_mcp_mode:
                self.colored_print("⚠️ 配置文件已存在，拒绝覆盖以保护用户数据", Fore.YELLOW)
            return
            
        default_config = {
            "servers": {
                "test": {
                    "description": "aa",
                    "host": "test.com",
                    "port": 22,
                    "username": "xuyehua",
                    "specs": {
                        "connection": {
                            "target": {
                                "host": "test.com"
                            },
                            "tool": "relay"
                        },
                        "docker": {
                            "container": "xyh_pytorch"
                        },
                        "environment": {
                            "BOS_BUCKET": "bos:/klx-pytorch-work-bd-bj/xuyehua/template",
                            "TMUX_SESSION_PREFIX": "test_dev"
                        }
                    }
                }
            },
            "global_settings": {
                "default_timeout": 30,
                "auto_recovery": True,
                "log_level": "INFO",
                "default_shell": "bash"
            },
            "security_settings": {
                "strict_host_key_checking": False,
                "connection_timeout": 30,
                "max_retry_attempts": 3
            }
        }
        
        try:
            # 再次检查文件是否存在（防止竞争条件）
            if config_file.exists():
                if not self.is_mcp_mode:
                    self.colored_print("⚠️ 配置文件在创建过程中已被其他进程创建，跳过", Fore.YELLOW)
                return
            
            with open(config_file, 'w', encoding='utf-8') as f:
                # 写入注释和配置
                f.write("# Remote Terminal MCP Configuration Template\n")
                f.write("# This file is automatically created when no config exists\n")
                f.write(f"# Generated at: {__import__('datetime').datetime.now().isoformat()}\n\n")
                
                # 写入实际配置
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
                
                # 添加使用说明
                f.write("\n# 使用说明:\n")
                f.write("# 1. 修改 example-server 的配置信息为你的实际服务器\n")
                f.write("# 2. 或者删除 example-server，添加你自己的服务器配置\n")
                f.write("# 3. 保存文件后，使用 remote-terminal-mcp 工具连接服务器\n")
                f.write("# 4. 更多配置选项请参考文档\n")
                
            if not self.is_mcp_mode:
                self.colored_print("✅ 默认配置文件已创建", Fore.GREEN)
                
        except Exception as e:
            if not self.is_mcp_mode:
                self.colored_print(f"❌ 创建默认配置失败: {e}", Fore.RED)
            raise

def main():
    """主函数"""
    try:
        config_manager = EnhancedConfigManager()
        config_manager.main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 用户取消操作，再见！")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()