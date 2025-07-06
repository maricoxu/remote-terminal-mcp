#!/usr/bin/env python3
"""
Enhanced Configuration Manager for Remote Terminal MCP
"""

import os
import sys
import yaml
import re
from typing import Dict, Optional, Tuple, Any, List
from pathlib import Path
import argparse
import json
import paramiko
import getpass
import glob

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore:
        RED = GREEN = YELLOW = CYAN = WHITE = ""
    class Style:
        BRIGHT = RESET_ALL = ""

class EnhancedConfigManager:
    def __init__(self, config_path: str = None):
        self.is_mcp_mode = (os.environ.get('MCP_MODE') == '1' or not sys.stdout.isatty())
        self.config_path = Path(config_path) if config_path else Path.home() / '.remote-terminal' / 'config.yaml'

    def colored_print(self, text: str, color=Fore.WHITE, style=""):
        if not self.is_mcp_mode:
            print(f"{color}{style}{text}{Style.RESET_ALL}")
        else:
            pass

    def show_progress(self, step: int, total: int, name: str):
        bar = "█" * step + "░" * (total - step)
        self.colored_print(f"\n📊 [{bar}] {step}/{total}: {name}", Fore.CYAN)

    def smart_input(self, prompt: str, validator=None, default=""):
        if self.is_mcp_mode: return default
        p_text = f"{prompt} [{default}]: " if default else f"{prompt}: "
        while True:
            try:
                val = input(p_text).strip()
                val = val or default
                if validator and not validator(val):
                    self.colored_print("❌ 输入无效。", Fore.RED)
                    continue
                return val
            except KeyboardInterrupt:
                return None

    def parse_user_host(self, user_host: str) -> Optional[Tuple[str, str]]:
        if '@' in user_host and len(user_host.split('@')) == 2:
            user, host = user_host.split('@', 1)
            if user and host:
                return user, host
        return None

    def validate_port(self, port: str) -> bool:
        return port.isdigit() and 1 <= int(port) <= 65535

    def get_existing_servers(self) -> dict:
        if not self.config_path.exists(): return {}
        try:
            with self.config_path.open('r', encoding='utf-8') as f:
                content = f.read()
            return yaml.safe_load(content).get('servers', {}) if content and content.strip() else {}
        except Exception:
            return {}

    def save_config(self, config: dict, merge: bool = True):
        final_cfg = config
        if merge and self.config_path.exists():
            existing = self.get_existing_servers()
            existing.update(config.get('servers', {}))
            final_cfg = {'servers': existing}
        
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open('w', encoding='utf-8') as f:
            yaml.dump(final_cfg, f, allow_unicode=True)
        self.colored_print(f"\n✅ 配置已保存至 {self.config_path}", Fore.GREEN)

    def _configure_password(self, prefill: dict = None, is_jump_host: bool = False) -> Optional[str]:
        label = "跳板机" if is_jump_host else "最终目标服务器"
        prefill = prefill or {}
        self.colored_print(f"\n🔐 配置{label}密码（可选）...", Fore.CYAN)
        self.colored_print("💡 如果使用密钥认证，请直接回车跳过", Fore.YELLOW)
        
        default_password = prefill.get('password', '')
        if self.is_mcp_mode:
            return default_password

        if default_password:
            password_prompt = f"密码已设置，回车保持不变，输入 'new' 重设: "
            choice = self.smart_input(password_prompt, default="keep")
            if choice.lower() == 'new':
                return getpass.getpass(f"请输入新的{label}密码: ")
            return default_password
        else:
            return getpass.getpass(f"请输入{label}密码 (回车跳过): ")

    def _fetch_remote_docker_containers(self, server_info: dict) -> Optional[List[str]]:
        self.colored_print("\n⏳ 正在连接服务器以获取容器列表...", Fore.YELLOW)
        client = None
        try:
            is_relay = server_info.get('connection_type') == 'relay'
            docker_host_info = server_info.get('jump_host', {}) if is_relay else server_info
            
            if not docker_host_info.get('host'):
                self.colored_print(f"❌ 无法确定运行Docker的主机地址。", Fore.RED)
                return None

            self.colored_print(f"ℹ️ 尝试连接到Docker主机: {docker_host_info.get('username')}@{docker_host_info.get('host')}", Fore.CYAN)
            
            password = docker_host_info.get('password')
            if not password:
                try:
                    password = getpass.getpass(f"请输入 {docker_host_info.get('username')}@{docker_host_info.get('host')} 的临时密码: ")
                except (EOFError, KeyboardInterrupt):
                    self.colored_print("\n操作取消。", Fore.YELLOW)
                    return None

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            client.connect(
                hostname=docker_host_info.get('host'),
                port=int(docker_host_info.get('port', 22)),
                username=docker_host_info.get('username'),
                password=password,
                timeout=10
            )

            stdin, stdout, stderr = client.exec_command('docker ps --format "{{.Names}}"')
            exit_status = stdout.channel.recv_exit_status()

            if exit_status != 0:
                error_output = stderr.read().decode().strip()
                if "command not found" in error_output.lower() or "not recognized" in error_output.lower() or "cannot connect" in error_output.lower():
                     self.colored_print(f"⚠️ 目标服务器上似乎未安装或未运行Docker。", Fore.YELLOW)
                else:
                    self.colored_print(f"⚠️ 获取容器列表失败: {error_output}", Fore.YELLOW)
                return None

            containers = stdout.read().decode().splitlines()
            if not containers:
                self.colored_print("🤔 未在服务器上发现正在运行的Docker容器。", Fore.YELLOW)
                return []
            
            self.colored_print("✅ 成功获取容器列表！", Fore.GREEN)
            return containers

        except paramiko.AuthenticationException:
            self.colored_print(f"❌ 认证失败，请检查主机 {docker_host_info.get('host')} 的密码或密钥。", Fore.RED)
            return None
        except Exception as e:
            self.colored_print(f"❌ 无法连接到服务器 {docker_host_info.get('host')}: {e}", Fore.RED)
            return None
        finally:
            if client:
                client.close()

    def _select_docker_template(self) -> dict:
        self.colored_print("\n📋 是否使用Docker模板进行快速配置？", Fore.CYAN)
        self.colored_print("1. 是，从模板列表选择\n2. 否，手动配置", Fore.WHITE)
        
        choice = self.smart_input("选择", default="2")
        if choice != "1":
            return {}

        template_dir = Path(__file__).resolve().parent.parent / 'docker_templates'
        if not template_dir.is_dir():
            self.colored_print(f"⚠️ 模板目录未找到: {template_dir}", Fore.YELLOW)
            return {}

        templates = sorted(list(template_dir.glob('*.yaml')))
        if not templates:
            self.colored_print(f"⚠️ 在 {template_dir} 中未找到任何模板文件。", Fore.YELLOW)
            return {}

        self.colored_print("\n请从以下可用模板中选择一个:", Fore.CYAN)
        for i, path in enumerate(templates):
            self.colored_print(f"{i+1}. {path.stem}", Fore.WHITE)

        while True:
            try:
                idx_choice = self.smart_input("选择模板编号", default="1")
                idx = int(idx_choice) - 1
                if 0 <= idx < len(templates):
                    selected_path = templates[idx]
                    with selected_path.open('r', encoding='utf-8') as f:
                        template_data = yaml.safe_load(f)
                    self.colored_print(f"✅ 已加载模板: {selected_path.stem}", Fore.GREEN)
                    return template_data
                else:
                    self.colored_print("❌ 无效的编号，请重新输入。", Fore.RED)
            except (ValueError, IndexError):
                self.colored_print("❌ 输入无效，请输入列表中的编号。", Fore.RED)

    def _configure_docker(self, defaults: dict = None, server_info: dict = None) -> Optional[dict]:
        prefill = defaults or {}
        server_info = server_info or {}
        self.colored_print(f"\n🐳 配置Docker设置...", Fore.CYAN)
        
        if prefill and not prefill.get('enabled', True):
             return None

        docker_enabled = prefill.get('enabled', False)
        default_choice = "1" if docker_enabled else "2"
        
        self.colored_print("1. 启用Docker容器支持\n2. 不使用Docker", Fore.WHITE)
        choice = self.smart_input("选择", default=default_choice)
        
        if choice != "1":
            return None
        
        docker_config = {'use_existing': False}

        use_existing_template = prefill.get('use_existing', False)
        default_existing_choice = "1" if use_existing_template else "2"
        self.colored_print("\n1. 使用已存在的Docker容器\n2. 创建并使用新容器", Fore.WHITE)
        existing_choice = self.smart_input("选择", default=default_existing_choice)
        
        if existing_choice == "1":
            docker_config['use_existing'] = True
            containers = self._fetch_remote_docker_containers(server_info)
            
            if containers is None:
                self.colored_print("⚠️ 获取容器列表失败。是否手动输入容器名？", Fore.YELLOW)
                self.colored_print("1. 是，我记得容器名\n2. 否，返回并创建新容器", Fore.WHITE)
                fallback_choice = self.smart_input("选择", default="2")
                if fallback_choice != "1":
                    docker_config['use_existing'] = False
                else:
                    container_name = self.smart_input("请输入容器名")
                    if not container_name:
                        docker_config['use_existing'] = False
                    else:
                        docker_config['container_name'] = container_name
            
            elif not containers:
                self.colored_print("🤔 未发现正在运行的容器。将引导您创建新容器。", Fore.YELLOW)
                docker_config['use_existing'] = False
            
            else:
                self.colored_print("\n请从以下列表中选择一个容器:", Fore.CYAN)
                for i, name in enumerate(containers):
                    self.colored_print(f"{i+1}. {name}", Fore.WHITE)
                
                default_container_idx = "1"
                if prefill.get('container_name') in containers:
                    default_container_idx = str(containers.index(prefill.get('container_name')) + 1)
                
                while True:
                    container_choice = self.smart_input("选择容器编号", default=default_container_idx)
                    if container_choice.isdigit() and 1 <= int(container_choice) <= len(containers):
                        docker_config['container_name'] = containers[int(container_choice)-1]
                        break
                    else:
                        self.colored_print("❌ 输入无效，请输入列表中的编号。", Fore.RED)

        if not docker_config.get('use_existing'):
            docker_config['image'] = self.smart_input("输入Docker镜像", default=prefill.get('image', ''))
            docker_config['container_name'] = self.smart_input("为容器命名", default=prefill.get('container_name', ''))
            docker_config['ports'] = self._collect_list_items("端口", prefill.get('ports', []))
            docker_config['volumes'] = self._collect_list_items("卷", prefill.get('volumes', []))
            docker_config['shell'] = self.smart_input("容器内使用的shell", default=prefill.get('shell', 'bash'))
            docker_config['extra_args'] = self.smart_input("额外的Docker运行参数", default=prefill.get('extra_args', ''))
            docker_config['restart_policy'] = self.smart_input("重启策略", default=prefill.get('restart_policy', 'unless-stopped'))
        
        return docker_config

    def _configure_sync(self, defaults: dict = None, server_config: dict = None) -> Optional[dict]:
        """
        配置自动同步设置
        
        Args:
            defaults: 默认配置
            server_config: 服务器配置信息
            
        Returns:
            dict: 同步配置信息，如果不启用同步则返回None
        """
        prefill = defaults or {}
        server_config = server_config or {}
        
        self.colored_print(f"\n🔄 配置自动同步设置...", Fore.CYAN)
        self.colored_print("💡 AutoSyncManager可以自动部署proftpd服务器，实现本地与远程的文件同步", Fore.YELLOW)
        
        # 步骤1: 是否开启自动同步
        sync_enabled = prefill.get('enabled', False)
        default_choice = "1" if sync_enabled else "2"
        
        self.colored_print("\n1. 启用自动同步 (推荐，用于开发环境)", Fore.WHITE)
        self.colored_print("2. 不使用自动同步", Fore.WHITE)
        choice = self.smart_input("选择", default=default_choice)
        
        if choice != "1":
            self.colored_print("🔕 已禁用自动同步功能", Fore.YELLOW)
            return None
        
        # 步骤2: 配置同步参数
        sync_config = {'enabled': True}
        
        # 远程同步目录
        default_remote_workspace = prefill.get('remote_workspace', '/home/Code')
        self.colored_print(f"\n📁 远程同步目录配置:", Fore.CYAN)
        self.colored_print("💡 这是远程服务器上存放代码的目录", Fore.YELLOW)
        sync_config['remote_workspace'] = self.smart_input(
            "远程工作目录", 
            default=default_remote_workspace
        )
        
        # FTP服务配置
        self.colored_print(f"\n🌐 FTP服务配置:", Fore.CYAN)
        self.colored_print("💡 AutoSyncManager会自动部署proftpd服务器", Fore.YELLOW)
        
        # FTP端口
        default_ftp_port = prefill.get('ftp_port', 8021)
        sync_config['ftp_port'] = self.smart_input(
            "FTP端口", 
            default=str(default_ftp_port),
            validator=self.validate_port
        )
        
        # FTP用户名
        default_ftp_user = prefill.get('ftp_user', 'ftpuser')
        sync_config['ftp_user'] = self.smart_input(
            "FTP用户名", 
            default=default_ftp_user
        )
        
        # FTP密码
        default_ftp_password = prefill.get('ftp_password', 'sync_password')
        sync_config['ftp_password'] = self.smart_input(
            "FTP密码", 
            default=default_ftp_password
        )
        
        # 本地工作目录
        default_local_workspace = prefill.get('local_workspace', '')
        self.colored_print(f"\n💻 本地同步配置:", Fore.CYAN)
        self.colored_print("💡 本地工作目录，空表示使用当前目录", Fore.YELLOW)
        sync_config['local_workspace'] = self.smart_input(
            "本地工作目录 (空表示当前目录)", 
            default=default_local_workspace
        )
        
        # 同步模式配置
        self.colored_print(f"\n🔄 同步模式配置:", Fore.CYAN)
        self.colored_print("💡 可以配置包含和排除的文件模式", Fore.YELLOW)
        
        # 包含模式
        default_include_patterns = prefill.get('include_patterns', ['*.py', '*.js', '*.md', '*.txt'])
        self.colored_print(f"包含模式默认值: {', '.join(default_include_patterns)}", Fore.YELLOW)
        include_patterns = self._collect_sync_patterns("包含模式", default_include_patterns)
        sync_config['include_patterns'] = include_patterns
        
        # 排除模式
        default_exclude_patterns = prefill.get('exclude_patterns', ['*.pyc', '__pycache__', '.git', 'node_modules'])
        self.colored_print(f"排除模式默认值: {', '.join(default_exclude_patterns)}", Fore.YELLOW)
        exclude_patterns = self._collect_sync_patterns("排除模式", default_exclude_patterns)
        sync_config['exclude_patterns'] = exclude_patterns
        
        # 配置摘要
        self.colored_print(f"\n📋 自动同步配置摘要:", Fore.GREEN)
        self.colored_print(f"  🗂️  远程目录: {sync_config['remote_workspace']}", Fore.WHITE)
        self.colored_print(f"  🌐 FTP端口: {sync_config['ftp_port']}", Fore.WHITE)
        self.colored_print(f"  👤 FTP用户: {sync_config['ftp_user']}", Fore.WHITE)
        self.colored_print(f"  🔐 FTP密码: {'*' * len(sync_config['ftp_password'])}", Fore.WHITE)
        local_dir = sync_config['local_workspace'] or "当前目录"
        self.colored_print(f"  💻 本地目录: {local_dir}", Fore.WHITE)
        self.colored_print(f"  ✅ 包含模式: {', '.join(include_patterns)}", Fore.WHITE)
        self.colored_print(f"  ❌ 排除模式: {', '.join(exclude_patterns)}", Fore.WHITE)
        
        return sync_config

    def _collect_sync_patterns(self, pattern_type: str, defaults: list = None) -> list:
        """
        收集同步模式配置
        
        Args:
            pattern_type: 模式类型（包含模式/排除模式）
            defaults: 默认值列表
            
        Returns:
            list: 配置的模式列表
        """
        patterns = []
        defaults = defaults or []
        
        self.colored_print(f"\n配置{pattern_type} (例如: *.py, *.js, __pycache__):", Fore.CYAN)
        self.colored_print("💡 留空完成配置", Fore.YELLOW)
        
        # 先处理默认值
        for i, default_pattern in enumerate(defaults):
            prompt = f"编辑 {pattern_type} #{i+1} (或回车保留)"
            pattern = self.smart_input(prompt, default=default_pattern)
            if pattern:
                patterns.append(pattern)
        
        # 添加新的模式
        i = len(defaults)
        while True:
            i += 1
            pattern = self.smart_input(f"新的{pattern_type} #{i}")
            if pattern:
                patterns.append(pattern)
            else:
                break
        
        return patterns if patterns else defaults

    def _collect_list_items(self, item_name: str, defaults: list = None) -> list:
        items = []
        defaults = defaults or []
        self.colored_print(f"\n配置{item_name} (例如 {'8080:80' if item_name == '端口' else '/host:/container'})，留空完成:", Fore.CYAN)
        if defaults:
            self.colored_print(f"模板默认值: {', '.join(defaults)}", Fore.YELLOW)

        for i, default_val in enumerate(defaults):
            prompt = f"编辑 {item_name} #{i+1} (或回车保留)"
            item = self.smart_input(prompt, default=default_val)
            if item:
                items.append(item)

        i = len(defaults)
        while True:
            i += 1
            item = self.smart_input(f"新的{item_name} #{i}")
            if item:
                items.append(item)
            else:
                return items

    def _configure_server(self, label: str, prefill: dict = None) -> Optional[dict]:
        prefill = prefill or {}
        self.colored_print(f"\n⚙️  配置 {label}...", Fore.CYAN)
        
        user, host = self._get_user_host(prefill)
        if not user or not host: return None
        
        port = self._get_port(prefill)
        if not port: return None
        
        server_info = {"host": host, "username": user, "port": int(port)}
        
        password = self._configure_password(server_info, is_jump_host=("跳板机" in label))
        if password:
            server_info['password'] = password
            
        return server_info

    def guided_setup(self, prefill_params: dict = None):
        self.colored_print("\n" + "="*50, Fore.GREEN, style=Style.BRIGHT)
        self.colored_print("欢迎使用远程终端配置向导", Fore.GREEN, style=Style.BRIGHT)
        self.colored_print("="*50, Fore.GREEN)
        
        prefill = prefill_params or {}
        
        server_name = self._get_server_name(prefill)
        if not server_name: return

        existing_servers = self.get_existing_servers()
        if server_name in existing_servers:
            self.colored_print(f"\n🔄 检测到服务器 '{server_name}' 已存在，进入更新模式。", Fore.YELLOW)
            defaults = existing_servers[server_name]
        else:
            self.colored_print(f"\n✨ 正在创建新服务器: {server_name}", Fore.CYAN)
            defaults = prefill
        
        final_config = {}

        self.show_progress(2, 6, "连接类型")
        final_config['connection_type'] = self._get_connection_type(defaults)
        if not final_config['connection_type']: return None

        self.show_progress(3, 6, "服务器配置")
        if final_config['connection_type'] == 'relay':
            final_config['jump_host'] = self._configure_server("跳板机", defaults.get('jump_host', {}))
            if not final_config['jump_host']: return None
            final_config.update(self._configure_server("最终目标服务器", defaults))
        else:
            final_config.update(self._configure_server("服务器", defaults))
        
        if not final_config.get('host'): return None

        self.show_progress(4, 7, "Docker配置")
        template_defaults = self._select_docker_template()
        docker_defaults = {**template_defaults, **defaults.get('docker_config', {})}
        docker_host_info = final_config.get('jump_host', final_config)

        docker_config = self._configure_docker(defaults=docker_defaults, server_info=docker_host_info)
        
        final_config['docker_enabled'] = bool(docker_config)
        final_config['docker_config'] = docker_config if docker_config else {}

        # 按照用户建议添加自动同步配置步骤
        self.show_progress(5, 7, "自动同步配置")
        sync_config = self._configure_sync(defaults.get('sync_config', {}), final_config)
        
        final_config['auto_sync_enabled'] = bool(sync_config)
        final_config['sync_config'] = sync_config if sync_config else {}

        self.show_progress(6, 7, "保存配置")
        self.colored_print("\n🎉 配置完成!", Fore.GREEN, style=Style.BRIGHT)
        self.save_config({'servers': {server_name: final_config}}, merge=True)
        return server_name, final_config

    def _get_user_host(self, prefill: dict) -> Tuple[Optional[str], Optional[str]]:
        default_uh = f"{prefill.get('username','')}@{prefill.get('host','')}" if prefill.get('username') and prefill.get('host') else ""
        while True:
            user_host_str = self.smart_input("输入服务器地址 (格式: user@host)", default=default_uh)
            if not user_host_str: return None, None
            parsed = self.parse_user_host(user_host_str)
            if parsed:
                return parsed
            self.colored_print("❌ 格式错误，请使用 'user@host' 格式。", Fore.RED)

    def _get_port(self, prefill: dict) -> Optional[str]:
        return self.smart_input("输入SSH端口", default=str(prefill.get("port", "22")), validator=self.validate_port)

    def _get_connection_type(self, prefill: dict) -> Optional[str]:
        self.colored_print("1. SSH直连\n2. Relay跳板机连接", Fore.WHITE)
        default = "2" if prefill.get('connection_type') == 'relay' else "1"
        choice = self.smart_input("选择连接类型", default=default)
        if choice == "1": return "ssh"
        if choice == "2": return "relay"
        return None

    def _get_server_name(self, prefill: dict) -> Optional[str]:
        return self.smart_input("为这个连接设置一个唯一的名称", default=prefill.get('name', ''))

def main():
    parser = argparse.ArgumentParser(description='Enhanced Configuration Manager for Remote Terminal MCP')
    args = parser.parse_args()
    manager = EnhancedConfigManager()
    manager.guided_setup()

if __name__ == "__main__":
    main()
