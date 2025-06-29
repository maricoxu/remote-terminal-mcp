#!/usr/bin/env python3
"""
Enhanced Configuration Manager for Remote Terminal MCP
"""

import os
import sys
import yaml
import re
from typing import Dict, Optional, Tuple, Any
from pathlib import Path
import argparse
import json

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
        # 在MCP模式下完全禁用输出以避免控制字符污染
        else:
            # 在MCP模式下，完全禁用输出以避免控制字符污染
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

    def _configure_password(self, prefill: dict = None) -> Optional[str]:
        """配置服务器密码（可选）"""
        prefill = prefill or {}
        self.colored_print(f"\n🔐 配置服务器密码（可选）...", Fore.CYAN)
        self.colored_print("💡 如果使用密钥认证，请直接回车跳过", Fore.YELLOW)
        
        default_password = prefill.get('password', '')
        if default_password:
            # 不显示密码，只显示提示
            password = self.smart_input("密码 (已设置，回车保持不变，输入new重新设置)", default="keep")
            if password == "new":
                password = self.smart_input("请输入新密码", default="")
            elif password == "keep":
                password = default_password
        else:
            password = self.smart_input("密码 (回车跳过，使用密钥认证)", default="")
        
        return password if password else None

    def _configure_docker(self, prefill: dict = None) -> Optional[dict]:
        """配置Docker设置"""
        prefill = prefill or {}
        self.colored_print(f"\n🐳 配置Docker设置...", Fore.CYAN)
        
        # 检查是否启用Docker
        docker_enabled = prefill.get('docker_enabled', False)
        default_choice = "1" if docker_enabled else "2"
        
        self.colored_print("1. 启用Docker容器支持\n2. 不使用Docker", Fore.WHITE)
        choice = self.smart_input("选择", default=default_choice)
        
        if choice != "1":
            return None
        
        # Docker配置
        docker_config = {}
        
        # Docker镜像
        default_image = prefill.get('docker_image', 'ubuntu:20.04')
        docker_config['image'] = self.smart_input("Docker镜像", default=default_image)
        
        # 容器名称
        default_container = prefill.get('docker_container', f"{prefill.get('name', 'server')}_container")
        docker_config['container_name'] = self.smart_input("容器名称", default=default_container)
        
        # 端口映射
        default_ports = prefill.get('docker_ports', ['8080:8080', '8888:8888', '6006:6006'])
        self.colored_print("端口映射配置 (格式: host_port:container_port)", Fore.YELLOW)
        ports = []
        for i, default_port in enumerate(default_ports):
            port = self.smart_input(f"端口映射 {i+1} (回车跳过)", default=default_port)
            if port:
                ports.append(port)
        
        # 允许添加更多端口
        while True:
            additional_port = self.smart_input("添加更多端口映射 (回车完成)", default="")
            if not additional_port:
                break
            ports.append(additional_port)
        
        docker_config['ports'] = ports
        
        # 卷挂载
        default_volumes = prefill.get('docker_volumes', ['/home:/home', '/data:/data'])
        self.colored_print("卷挂载配置 (格式: host_path:container_path)", Fore.YELLOW)
        volumes = []
        for i, default_volume in enumerate(default_volumes):
            volume = self.smart_input(f"卷挂载 {i+1} (回车跳过)", default=default_volume)
            if volume:
                volumes.append(volume)
        
        # 允许添加更多卷挂载
        while True:
            additional_volume = self.smart_input("添加更多卷挂载 (回车完成)", default="")
            if not additional_volume:
                break
            volumes.append(additional_volume)
        
        docker_config['volumes'] = volumes
        
        # Shell类型
        default_shell = prefill.get('docker_shell', 'bash')
        docker_config['shell'] = self.smart_input("容器内Shell", default=default_shell)
        
        # 自动创建容器
        default_auto_create = prefill.get('docker_auto_create', True)
        auto_choice = "1" if default_auto_create else "2"
        self.colored_print("1. 自动创建容器（如果不存在）\n2. 手动管理容器", Fore.WHITE)
        auto_create_choice = self.smart_input("选择", default=auto_choice)
        docker_config['auto_create'] = (auto_create_choice == "1")
        
        return docker_config

    def _configure_server(self, label: str, prefill: dict = None) -> Optional[dict]:
        prefill = prefill or {}
        self.colored_print(f"\n🚀 配置 {label}...", Fore.CYAN)
        default_uh = f"{prefill.get('username','')}@{prefill.get('host','')}" if prefill.get('username') else ""
        user_host = self.smart_input("地址 (user@host)", default=default_uh)
        if not user_host: return None
        
        parsed = self.parse_user_host(user_host)
        if not parsed: 
            self.colored_print("格式错误。", Fore.RED)
            return None
        user, host = parsed

        port = self.smart_input("端口", default=str(prefill.get("port", "22")), validator=self.validate_port)
        if not port: return None
        
        return {"host": host, "username": user, "port": int(port)}

    def launch_cursor_terminal_config(self, prefill_params: dict = None):
        """
        启动Cursor终端配置界面
        这个方法被MCP服务器调用来启动交互配置界面
        """
        try:
            import tempfile
            import subprocess
            import json
            
            # 如果有预填充参数，创建临时文件
            temp_file = None
            if prefill_params:
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
                json.dump(prefill_params, temp_file, ensure_ascii=False, indent=2)
                temp_file.close()
            
            # 构建启动命令
            cmd = [
                'python3', 
                str(Path(__file__).resolve()),
                '--cursor-terminal'
            ]
            
            if temp_file:
                cmd.extend(['--prefill', temp_file.name])
            
            # 启动新终端进程
            process = subprocess.Popen(
                cmd,
                cwd=str(Path(__file__).parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            return {
                "success": True,
                "process_id": f"new_terminal_window",
                "prefill_file": temp_file.name if temp_file else None,
                "command": ' '.join(cmd)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def guided_setup(self, prefill_params: dict = None):
        self.colored_print("\n" + "="*50, Fore.GREEN, style=Style.BRIGHT)
        self.colored_print("欢迎使用远程终端配置向导", Fore.GREEN, style=Style.BRIGHT)
        self.colored_print("="*50, Fore.GREEN)

        prefill_params = prefill_params or {}
        servers = self.get_existing_servers()
        name_default = prefill_params.get('name', '')
        
        if name_default and name_default in servers:
            self.colored_print(f"ℹ️ 正在更新: {name_default}", Fore.CYAN)
            defaults = servers.get(name_default, {})
        else:
            self.colored_print("✨ 正在创建新服务器...", Fore.CYAN)
            defaults = prefill_params

        self.show_progress(1, 6, "服务器名称")
        name = self.smart_input("为服务器取个名字", default=name_default)
        if not name: return

        # 根据用户实际输入的服务器名称来决定配置参数
        if name in servers:
            self.colored_print(f"ℹ️ 正在更新现有服务器: {name}", Fore.YELLOW)
            cfg_params = servers[name]  # 使用现有服务器的配置作为默认值
        else:
            self.colored_print(f"✨ 正在创建新服务器: {name}", Fore.GREEN)
            cfg_params = prefill_params  # 使用prefill参数作为默认值

        self.show_progress(2, 6, "连接方式")
        self.colored_print("1. Relay跳板机连接\n2. SSH直连", Fore.WHITE)
        conn_choice = self.smart_input("选择", default="1" if cfg_params.get('connection_type') == 'relay' else "2")
        if not conn_choice: return

        self.show_progress(3, 6, "服务器信息")
        new_cfg = {}
        if conn_choice == '1': # Relay
            new_cfg['connection_type'] = 'relay'
            relay_params = self._configure_server("中继/跳板机", prefill=cfg_params)
            if not relay_params: return
            new_cfg.update(relay_params)
            
            target_defaults = cfg_params.get('specs', {}).get('connection', {}).get('jump_host', {})
            target_params = self._configure_server("最终目标服务器", prefill=target_defaults)
            if not target_params: return
            new_cfg.setdefault('specs', {}).setdefault('connection', {})['jump_host'] = target_params
        else: # SSH
            new_cfg['connection_type'] = 'ssh'
            ssh_params = self._configure_server("SSH服务器", prefill=cfg_params)
            if not ssh_params: return
            new_cfg.update(ssh_params)

        # 第4步：配置密码
        self.show_progress(4, 6, "密码配置")
        password = self._configure_password(prefill=cfg_params)
        if password:
            new_cfg['password'] = password

        # 第5步：配置Docker
        self.show_progress(5, 6, "Docker配置")
        docker_config = self._configure_docker(prefill=cfg_params)
        if docker_config:
            new_cfg['docker_enabled'] = True
            new_cfg['docker_image'] = docker_config['image']
            new_cfg['docker_container'] = docker_config['container_name']
            new_cfg['docker_ports'] = docker_config['ports']
            new_cfg['docker_volumes'] = docker_config['volumes']
            new_cfg['docker_shell'] = docker_config['shell']
            new_cfg['docker_auto_create'] = docker_config['auto_create']
        else:
            new_cfg['docker_enabled'] = False

        self.show_progress(6, 6, "保存配置")
        self.save_config({"servers": {name: new_cfg}})

def main():
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Enhanced Configuration Manager for Remote Terminal MCP')
    parser.add_argument('--cursor-terminal', action='store_true', help='在Cursor终端模式下运行')
    parser.add_argument('--prefill', type=str, help='预填充参数的JSON文件路径')
    parser.add_argument('--force-interactive', action='store_true', help='强制启动交互模式')
    parser.add_argument('--auto-close', action='store_true', help='完成后自动关闭')
    
    args = parser.parse_args()
    
    # 读取预填充参数
    prefill_params = {}
    if args.prefill:
        try:
            with open(args.prefill, 'r', encoding='utf-8') as f:
                prefill_params = json.load(f)
            print(f"✅ 已加载预填充参数: {args.prefill}")
        except Exception as e:
            print(f"⚠️ 无法读取预填充文件 {args.prefill}: {e}")
    
    manager = EnhancedConfigManager()
    
    # 如果有预填充参数且包含update_mode标记，显示更新信息
    if prefill_params.get('update_mode'):
        print(f"🔄 正在更新服务器配置: {prefill_params.get('name', '未知')}")
    
    manager.guided_setup(prefill_params=prefill_params)
    
    # 如果启用了自动关闭，清理临时文件
    if args.auto_close and args.prefill:
        try:
            import os
            os.unlink(args.prefill)
            print(f"🧹 已清理临时文件: {args.prefill}")
        except:
            pass

if __name__ == "__main__":
    main()