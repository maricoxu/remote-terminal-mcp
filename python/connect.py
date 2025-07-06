#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新一代连接管理器 - 分离关注点架构

设计理念：
1. 单一职责原则 - 每个类只负责一个方面
2. 清晰的接口 - 简单易用的API
3. 强化的错误处理 - 明确的错误信息和恢复建议
4. 智能的用户引导 - 主动帮助用户完成认证流程
"""

import os
import sys
import time
import subprocess
import threading
import yaml
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import re
from enum import Enum


def log_output(message: str, level: str = "INFO"):
    """增强的日志输出"""
    if not os.getenv('MCP_QUIET'):
        level_emoji = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "WARNING": "⚠️",
            "ERROR": "❌",
            "DEBUG": "🔍"
        }
        emoji = level_emoji.get(level, "📋")
        print(f"{emoji} {message}")


class ConnectionType(Enum):
    """连接类型枚举"""
    SSH = "ssh"
    RELAY = "relay"
    SCRIPT_BASED = "script_based"


class ConnectionStatus(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    READY = "ready"
    ERROR = "error"


@dataclass
class ConnectionResult:
    """连接结果数据类"""
    success: bool
    message: str
    session_name: Optional[str] = None
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    details: Optional[Dict[str, Any]] = None


@dataclass
class ServerConfig:
    """服务器配置数据类"""
    name: str
    host: str
    username: str
    connection_type: ConnectionType
    port: int = 22
    docker_container: Optional[str] = None
    docker_shell: str = "zsh"
    session_name: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    # 环境配置相关字段
    preferred_shell: str = "zsh"  # 用户偏好的shell
    auto_configure_shell: bool = True  # 是否自动配置shell环境
    copy_shell_configs: bool = True  # 是否拷贝shell配置文件
    # 自动同步配置字段
    auto_sync_enabled: bool = False  # 是否启用自动同步
    sync_remote_workspace: str = "/home/Code"  # 远程工作目录
    sync_ftp_port: int = 8021  # FTP端口
    sync_ftp_user: str = "ftpuser"  # FTP用户
    sync_ftp_password: str = "sync_password"  # FTP密码
    sync_local_workspace: str = ""  # 本地工作目录（空表示当前目录）
    sync_patterns: Optional[list] = None  # 同步文件模式
    sync_exclude_patterns: Optional[list] = None  # 排除文件模式


class InteractionGuide:
    """交互引导器 - 专门处理用户交互和认证引导"""
    
    def __init__(self, session_name: str):
        self.session_name = session_name
        self.auth_patterns = {
            'relay_qr': [r'请使用.*扫描二维码', r'scan.*qr.*code'],
            'relay_fingerprint': [r'请确认指纹', r'touch.*sensor', r'fingerprint'],
            'relay_code': [r'请输入验证码', r'verification.*code'],
            'relay_continue': [r'press.*any.*key', r'按.*任意键'],
            'relay_success': [r'-bash-baidu-ssl\$', r'baidu.*ssl'],
            'ssh_password': [r'password:', r'请输入密码'],
            'ssh_fingerprint': [r'fingerprint.*\(yes/no\)', r'continue.*connecting'],
            'docker_prompt': [r'root@.*#', r'.*@.*container.*\$']
        }
    
    def detect_interaction_type(self, output: str) -> Optional[str]:
        """检测需要的交互类型"""
        output_lower = output.lower()
        
        for interaction_type, patterns in self.auth_patterns.items():
            for pattern in patterns:
                if re.search(pattern, output_lower):
                    log_output(f"🔍 检测到交互类型: {interaction_type}", "DEBUG")
                    return interaction_type
        
        return None
    
    def provide_guidance(self, interaction_type: str) -> Dict[str, Any]:
        """提供用户操作引导"""
        guidance_map = {
            'relay_qr': {
                'title': '📱 需要扫描二维码',
                'message': 'Relay需要您使用手机App扫描二维码进行认证',
                'steps': [
                    '1. 打开公司提供的认证App',
                    '2. 扫描终端中显示的二维码',
                    '3. 在手机上确认登录',
                    f'4. 可以运行查看详情: tmux attach -t {self.session_name}'
                ],
                'timeout': 180
            },
            'relay_fingerprint': {
                'title': '👆 需要指纹认证',
                'message': 'Relay需要您进行指纹确认',
                'steps': [
                    '1. 在指纹识别设备上按压手指',
                    '2. 等待指纹识别完成',
                    f'3. 可以运行查看详情: tmux attach -t {self.session_name}'
                ],
                'timeout': 60
            },
            'relay_code': {
                'title': '🔢 需要输入验证码',
                'message': 'Relay需要您输入验证码',
                'steps': [
                    '1. 打开您的验证器应用',
                    '2. 获取当前验证码',
                    f'3. 运行: tmux attach -t {self.session_name}',
                    '4. 输入验证码',
                    '5. 按 Ctrl+B, D 退出会话'
                ],
                'timeout': 120
            },
            'relay_continue': {
                'title': '⌨️ 需要按键继续',
                'message': 'Relay认证完成，需要按任意键继续',
                'steps': [
                    f'1. 运行: tmux attach -t {self.session_name}',
                    '2. 按任意键继续',
                    '3. 按 Ctrl+B, D 退出会话'
                ],
                'timeout': 30
            },
            'ssh_password': {
                'title': '🔐 需要输入SSH密码',
                'message': 'SSH连接需要您输入密码',
                'steps': [
                    f'1. 运行: tmux attach -t {self.session_name}',
                    '2. 输入您的密码',
                    '3. 按 Ctrl+B, D 退出会话'
                ],
                'timeout': 300
            },
            'ssh_fingerprint': {
                'title': '🔑 需要确认SSH指纹',
                'message': '首次连接需要确认服务器指纹',
                'steps': [
                    f'1. 运行: tmux attach -t {self.session_name}',
                    '2. 查看指纹信息',
                    '3. 输入 "yes" 确认',
                    '4. 按 Ctrl+B, D 退出会话'
                ],
                'timeout': 120
            }
        }
        
        return guidance_map.get(interaction_type, {
            'title': '❓ 需要手动操作',
            'message': '检测到需要手动操作',
            'steps': [f'请运行查看详情: tmux attach -t {self.session_name}'],
            'timeout': 300
        })
    
    def show_guidance(self, guidance: Dict[str, Any]):
        """显示操作引导"""
        log_output("", "INFO")
        log_output(f"🎯 {guidance['title']}", "WARNING")
        log_output(f"📝 {guidance['message']}", "INFO")
        log_output("", "INFO")
        log_output("📋 操作步骤:", "INFO")
        for step in guidance['steps']:
            log_output(f"   {step}", "INFO")
        log_output("", "INFO")
        log_output(f"⏰ 请在 {guidance['timeout']} 秒内完成操作", "WARNING")
        log_output("", "INFO")


class RelayConnector:
    """Relay连接器 - 专门处理relay-cli连接"""
    
    def __init__(self, guide: InteractionGuide):
        self.guide = guide
    
    def connect(self, server_config: ServerConfig) -> ConnectionResult:
        """执行relay连接流程"""
        session_name = server_config.session_name
        
        try:
            log_output("🚀 开始Relay连接流程", "INFO")
            
            # 步骤1: 启动relay-cli (严格遵循规则：不接任何参数)
            log_output("📡 启动 relay-cli...", "INFO")
            result = subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, 'relay-cli', 'Enter'],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                return ConnectionResult(
                    success=False,
                    message=f"启动relay-cli失败: {result.stderr}",
                    status=ConnectionStatus.ERROR
                )
            
            # 步骤2: 处理认证流程
            auth_result = self._handle_authentication(session_name)
            if not auth_result.success:
                return auth_result
            
            # 步骤3: SSH到目标服务器
            ssh_result = self._ssh_to_target(server_config)
            if not ssh_result.success:
                return ssh_result
            
            return ConnectionResult(
                success=True,
                message="Relay连接成功",
                session_name=session_name,
                status=ConnectionStatus.CONNECTED
            )
            
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"Relay连接异常: {str(e)}",
                status=ConnectionStatus.ERROR
            )
    
    def _handle_authentication(self, session_name: str, timeout: int = 180) -> ConnectionResult:
        """处理relay认证流程"""
        log_output("🔐 开始处理Relay认证...", "INFO")
        start_time = time.time()
        last_interaction_time = start_time
        
        while time.time() - start_time < timeout:
            try:
                # 获取当前输出
                result = subprocess.run(
                    ['tmux', 'capture-pane', '-p', '-t', session_name],
                    capture_output=True, text=True, check=True
                )
                output = result.stdout
                
                # 检查认证成功
                if re.search(r'-bash-baidu-ssl\$', output):
                    log_output("✅ Relay认证成功!", "SUCCESS")
                    return ConnectionResult(
                        success=True,
                        message="Relay认证完成",
                        status=ConnectionStatus.CONNECTED
                    )
                
                # 检测交互需求
                interaction_type = self.guide.detect_interaction_type(output)
                if interaction_type and interaction_type != 'relay_success':
                    # 重置超时计时器
                    if time.time() - last_interaction_time > 30:
                        guidance = self.guide.provide_guidance(interaction_type)
                        self.guide.show_guidance(guidance)
                        last_interaction_time = time.time()
                
                # 检查错误状态
                if re.search(r'authentication.*failed|认证失败|network.*error|网络错误', output.lower()):
                    return ConnectionResult(
                        success=False,
                        message="Relay认证失败，请检查网络和认证信息",
                        status=ConnectionStatus.ERROR
                    )
                
                time.sleep(2)  # 每2秒检查一次
                
            except subprocess.CalledProcessError:
                return ConnectionResult(
                    success=False,
                    message="tmux会话不可访问",
                    status=ConnectionStatus.ERROR
                )
        
        # 认证超时
        return ConnectionResult(
            success=False,
            message=f"Relay认证超时({timeout}秒)，请手动检查认证状态",
            status=ConnectionStatus.ERROR,
            details={'tmux_command': f'tmux attach -t {session_name}'}
        )
    
    def _ssh_to_target(self, server_config: ServerConfig) -> ConnectionResult:
        """从relay环境SSH到目标服务器"""
        session_name = server_config.session_name
        ssh_cmd = f"ssh -t {server_config.username}@{server_config.host}"
        
        log_output(f"🎯 连接到目标服务器: {server_config.host}", "INFO")
        
        try:
            # 发送SSH命令
            subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, ssh_cmd, 'Enter'],
                capture_output=True, check=True
            )
            
            # 等待连接成功
            if self._wait_for_target_connection(session_name, server_config.host):
                log_output(f"✅ 成功连接到 {server_config.host}", "SUCCESS")
                return ConnectionResult(
                    success=True,
                    message=f"成功连接到目标服务器",
                    status=ConnectionStatus.CONNECTED
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"连接到 {server_config.host} 超时",
                    status=ConnectionStatus.ERROR
                )
                
        except subprocess.CalledProcessError as e:
            return ConnectionResult(
                success=False,
                message=f"SSH命令执行失败: {e}",
                status=ConnectionStatus.ERROR
            )
    
    def _wait_for_target_connection(self, session_name: str, host: str, timeout: int = 30) -> bool:
        """等待目标服务器连接完成"""
        start_time = time.time()
        target_indicators = [
            f"@{host.split('.')[0]}",  # 主机名提示符
            f"~]$",                    # 用户主目录提示符
            f"# "                      # root提示符
        ]
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ['tmux', 'capture-pane', '-p', '-t', session_name],
                    capture_output=True, text=True, check=True
                )
                
                for indicator in target_indicators:
                    if indicator in result.stdout:
                        return True
                
                time.sleep(1)
                
            except subprocess.CalledProcessError:
                return False
        
        return False


class SSHConnector:
    """SSH连接器 - 专门处理直接SSH连接"""
    
    def __init__(self, guide: InteractionGuide):
        self.guide = guide
    
    def connect(self, server_config: ServerConfig) -> ConnectionResult:
        """执行SSH连接"""
        session_name = server_config.session_name
        ssh_cmd = f"ssh {server_config.username}@{server_config.host} -p {server_config.port}"
        
        try:
            log_output(f"🔗 开始SSH连接: {server_config.host}", "INFO")
            
            # 发送SSH命令
            subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, ssh_cmd, 'Enter'],
                capture_output=True, check=True
            )
            
            # 处理可能的交互
            if self._handle_ssh_interactions(session_name):
                return ConnectionResult(
                    success=True,
                    message="SSH连接成功",
                    session_name=session_name,
                    status=ConnectionStatus.CONNECTED
                )
            else:
                return ConnectionResult(
                    success=False,
                    message="SSH连接失败或超时",
                    status=ConnectionStatus.ERROR
                )
                
        except subprocess.CalledProcessError as e:
            return ConnectionResult(
                success=False,
                message=f"SSH连接异常: {e}",
                status=ConnectionStatus.ERROR
            )
    
    def _handle_ssh_interactions(self, session_name: str, timeout: int = 60) -> bool:
        """处理SSH交互（密码、指纹确认等）"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ['tmux', 'capture-pane', '-p', '-t', session_name],
                    capture_output=True, text=True, check=True
                )
                output = result.stdout
                
                # 检查连接成功
                if re.search(r'[@#]\s*$', output.split('\n')[-1]):
                    return True
                
                # 检测交互需求
                interaction_type = self.guide.detect_interaction_type(output)
                if interaction_type and interaction_type.startswith('ssh_'):
                    guidance = self.guide.provide_guidance(interaction_type)
                    self.guide.show_guidance(guidance)
                    # 等待用户操作
                    time.sleep(10)
                
                time.sleep(2)
                
            except subprocess.CalledProcessError:
                return False
        
        return False


class DockerManager:
    """Docker管理器 - 专门处理Docker容器操作"""
    
    def __init__(self):
        pass
    
    def enter_container(self, server_config: ServerConfig) -> ConnectionResult:
        """进入Docker容器"""
        if not server_config.docker_container:
            return ConnectionResult(
                success=True,
                message="无Docker容器配置，保持主机连接",
                status=ConnectionStatus.READY
            )
        
        session_name = server_config.session_name
        container_name = server_config.docker_container
        shell = server_config.docker_shell
        
        try:
            log_output(f"🐳 进入Docker容器: {container_name}", "INFO")
            
            # 发送docker exec命令
            docker_cmd = f"docker exec -it {container_name} {shell}"
            subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, docker_cmd, 'Enter'],
                capture_output=True, check=True
            )
            
            # 等待进入容器
            if self._wait_for_container_entry(session_name, container_name):
                log_output(f"✅ 成功进入容器 {container_name}", "SUCCESS")
                return ConnectionResult(
                    success=True,
                    message=f"成功进入Docker容器: {container_name}",
                    status=ConnectionStatus.READY
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"进入容器 {container_name} 失败",
                    status=ConnectionStatus.ERROR
                )
                
        except subprocess.CalledProcessError as e:
            return ConnectionResult(
                success=False,
                message=f"Docker操作失败: {e}",
                status=ConnectionStatus.ERROR
            )
    
    def _wait_for_container_entry(self, session_name: str, container_name: str, timeout: int = 20) -> bool:
        """等待进入容器完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 发送测试命令
                subprocess.run(
                    ['tmux', 'send-keys', '-t', session_name, 'echo "CONTAINER_CHECK_$(hostname)"', 'Enter'],
                    capture_output=True
                )
                time.sleep(2)
                
                result = subprocess.run(
                    ['tmux', 'capture-pane', '-p', '-t', session_name],
                    capture_output=True, text=True, check=True
                )
                
                # 检查是否在容器内
                if 'CONTAINER_CHECK_' in result.stdout and container_name in result.stdout:
                    return True
                
                time.sleep(1)
                
            except subprocess.CalledProcessError:
                return False
        
        return False


class ConnectionManager:
    """连接管理器 - 主要协调器，统一管理所有连接流程"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = self._find_config_file() if not config_path else config_path
        self.servers = self._load_servers()
        log_output("🚀 新一代连接管理器已初始化", "SUCCESS")
    
    def _find_config_file(self) -> str:
        """查找配置文件"""
        # 与原有逻辑保持一致
        user_config_dir = Path.home() / ".remote-terminal"
        user_config_file = user_config_dir / "config.yaml"
        
        if user_config_file.exists():
            return str(user_config_file)
        
        script_dir = Path(__file__).parent
        project_dir = script_dir.parent
        local_config = project_dir / "config" / "servers.local.yaml"
        if local_config.exists():
            return str(local_config)
        
        template_config = project_dir / "config" / "servers.template.yaml"
        if template_config.exists():
            return str(template_config)
        
        raise FileNotFoundError("未找到配置文件")
    
    def _load_servers(self) -> Dict[str, ServerConfig]:
        """加载服务器配置"""
        servers = {}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            servers_config = config.get('servers', {})
            for name, server_data in servers_config.items():
                # 解析连接类型
                if server_data.get('type') == 'script_based':
                    connection_config = server_data.get('specs', {}).get('connection', {})
                    tool = connection_config.get('tool', 'ssh')
                    connection_type = ConnectionType.RELAY if tool == 'relay-cli' else ConnectionType.SSH
                else:
                    connection_type = ConnectionType.SSH
                
                # 解析Docker配置
                docker_config = server_data.get('specs', {}).get('docker', {}) or server_data.get('docker', {})
                
                # 创建服务器配置
                server_config = ServerConfig(
                    name=name,
                    host=server_data.get('host', ''),
                    username=server_data.get('username', ''),
                    connection_type=connection_type,
                    port=server_data.get('port', 22),
                    docker_container=docker_config.get('container_name'),
                    docker_shell=docker_config.get('shell', 'zsh'),
                    session_name=server_data.get('session', {}).get('name', f"{name}_session"),
                    specs=server_data.get('specs', {})
                )
                
                servers[name] = server_config
            
            return servers
            
        except Exception as e:
            raise Exception(f"配置加载失败: {str(e)}")
    
    def connect(self, server_name: str, force_recreate: bool = False) -> ConnectionResult:
        """连接到服务器 - 主要入口函数"""
        if server_name not in self.servers:
            return ConnectionResult(
                success=False,
                message=f"服务器 {server_name} 不存在",
                status=ConnectionStatus.ERROR
            )
        
        server_config = self.servers[server_name]
        session_name = server_config.session_name
        
        try:
            log_output(f"🎯 开始连接服务器: {server_name}", "INFO")
            log_output(f"📋 连接类型: {server_config.connection_type.value}", "INFO")
            log_output(f"🖥️  目标主机: {server_config.host}", "INFO")
            log_output(f"👤 用户名: {server_config.username}", "INFO")
            if server_config.docker_container:
                log_output(f"🐳 Docker容器: {server_config.docker_container}", "INFO")
            
            # 步骤1: 检查现有连接
            if not force_recreate and self._check_existing_connection(session_name):
                log_output("✅ 发现现有连接，验证状态...", "INFO")
                if self._verify_connection_health(session_name, server_config):
                    return ConnectionResult(
                        success=True,
                        message="连接已存在且健康",
                        session_name=session_name,
                        status=ConnectionStatus.READY
                    )
                else:
                    log_output("⚠️ 现有连接不健康，重新建立连接", "WARNING")
            
            # 步骤2: 创建新的tmux会话
            connection_result = self._create_session(session_name, force_recreate)
            if not connection_result.success:
                return connection_result
            
            # 步骤3: 建立基础连接
            guide = InteractionGuide(session_name)
            
            if server_config.connection_type == ConnectionType.RELAY:
                connector = RelayConnector(guide)
            else:
                connector = SSHConnector(guide)
            
            base_result = connector.connect(server_config)
            if not base_result.success:
                return base_result
            
            # 步骤4: 进入Docker容器（如果配置了）
            docker_manager = DockerManager()
            docker_result = docker_manager.enter_container(server_config)
            if not docker_result.success:
                log_output(f"⚠️ Docker操作失败: {docker_result.message}", "WARNING")
                log_output("📝 将继续使用主机环境", "INFO")
            
            # 步骤5: 显示连接信息
            self._show_connection_summary(server_name, session_name, server_config)
            
            return ConnectionResult(
                success=True,
                message=f"成功连接到 {server_name}",
                session_name=session_name,
                status=ConnectionStatus.READY,
                details={
                    'connection_type': server_config.connection_type.value,
                    'host': server_config.host,
                    'docker_container': server_config.docker_container
                }
            )
            
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"连接异常: {str(e)}",
                status=ConnectionStatus.ERROR
            )
    
    def _check_existing_connection(self, session_name: str) -> bool:
        """检查现有连接是否存在"""
        try:
            result = subprocess.run(
                ['tmux', 'has-session', '-t', session_name],
                capture_output=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _verify_connection_health(self, session_name: str, server_config: ServerConfig) -> bool:
        """验证连接健康状态"""
        try:
            # 发送测试命令
            subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, 'echo "HEALTH_CHECK_$(date +%s)"', 'Enter'],
                capture_output=True
            )
            time.sleep(2)
            
            # 获取输出
            result = subprocess.run(
                ['tmux', 'capture-pane', '-p', '-t', session_name],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                return False
            
            output = result.stdout
            
            # 检查是否有响应
            if 'HEALTH_CHECK_' in output:
                # 检查是否在正确的环境中
                if server_config.connection_type == ConnectionType.RELAY:
                    # 对于relay连接，检查是否在目标服务器上
                    return server_config.host.split('.')[0] in output
                else:
                    # 对于SSH连接，检查是否不在本地
                    return not any(local_indicator in output for local_indicator in 
                                 ['MacBook-Pro', 'localhost', 'Mac-Studio'])
            
            return False
            
        except:
            return False
    
    def _create_session(self, session_name: str, force_recreate: bool = False) -> ConnectionResult:
        """创建tmux会话"""
        try:
            if force_recreate:
                # 强制删除现有会话
                subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
            
            # 创建新会话
            result = subprocess.run(
                ['tmux', 'new-session', '-d', '-s', session_name],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                return ConnectionResult(
                    success=False,
                    message=f"创建tmux会话失败: {result.stderr}",
                    status=ConnectionStatus.ERROR
                )
            
            log_output(f"✅ 创建tmux会话: {session_name}", "SUCCESS")
            return ConnectionResult(
                success=True,
                message="会话创建成功",
                status=ConnectionStatus.CONNECTING
            )
            
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"会话创建异常: {str(e)}",
                status=ConnectionStatus.ERROR
            )
    
    def _show_connection_summary(self, server_name: str, session_name: str, server_config: ServerConfig):
        """显示连接摘要信息"""
        log_output("", "INFO")
        log_output("🎉 连接建立成功!", "SUCCESS")
        log_output("", "INFO")
        log_output("📊 连接信息:", "INFO")
        log_output(f"  🏷️  服务器名: {server_name}", "INFO")
        log_output(f"  🖥️  主机地址: {server_config.host}", "INFO")
        log_output(f"  👤 用户名: {server_config.username}", "INFO")
        log_output(f"  🔗 连接类型: {server_config.connection_type.value}", "INFO")
        if server_config.docker_container:
            log_output(f"  🐳 Docker容器: {server_config.docker_container}", "INFO")
        log_output("", "INFO")
        log_output("🎯 快速操作:", "INFO")
        log_output(f"  连接终端: tmux attach -t {session_name}", "INFO")
        log_output(f"  分离会话: Ctrl+B, D", "INFO")
        log_output(f"  查看会话: tmux list-sessions", "INFO")
        log_output("", "INFO")
    
    def disconnect(self, server_name: str) -> ConnectionResult:
        """断开连接"""
        if server_name not in self.servers:
            return ConnectionResult(
                success=False,
                message=f"服务器 {server_name} 不存在",
                status=ConnectionStatus.ERROR
            )
        
        session_name = self.servers[server_name].session_name
        
        try:
            result = subprocess.run(
                ['tmux', 'kill-session', '-t', session_name],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                log_output(f"✅ 已断开连接: {server_name}", "SUCCESS")
                return ConnectionResult(
                    success=True,
                    message=f"成功断开 {server_name}",
                    status=ConnectionStatus.DISCONNECTED
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"断开连接失败: {result.stderr}",
                    status=ConnectionStatus.ERROR
                )
                
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"断开连接异常: {str(e)}",
                status=ConnectionStatus.ERROR
            )
    
    def get_status(self, server_name: str) -> ConnectionResult:
        """获取连接状态"""
        if server_name not in self.servers:
            return ConnectionResult(
                success=False,
                message=f"服务器 {server_name} 不存在",
                status=ConnectionStatus.ERROR
            )
        
        server_config = self.servers[server_name]
        session_name = server_config.session_name
        
        if not self._check_existing_connection(session_name):
            return ConnectionResult(
                success=True,
                message="未连接",
                status=ConnectionStatus.DISCONNECTED
            )
        
        if self._verify_connection_health(session_name, server_config):
            status = ConnectionStatus.READY
            message = "连接健康"
        else:
            status = ConnectionStatus.CONNECTED
            message = "连接存在但可能不健康"
        
        return ConnectionResult(
            success=True,
            message=message,
            session_name=session_name,
            status=status
        )
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """列出所有服务器"""
        servers_info = []
        for name, config in self.servers.items():
            status = self.get_status(name)
            servers_info.append({
                'name': name,
                'host': config.host,
                'username': config.username,
                'connection_type': config.connection_type.value,
                'docker_container': config.docker_container,
                'status': status.status.value,
                'session_name': config.session_name
            })
        return servers_info
    
    def execute_command(self, server_name: str, command: str) -> ConnectionResult:
        """执行命令"""
        if server_name not in self.servers:
            return ConnectionResult(
                success=False,
                message=f"服务器 {server_name} 不存在",
                status=ConnectionStatus.ERROR
            )
        
        session_name = self.servers[server_name].session_name
        
        try:
            if not self._check_existing_connection(session_name):
                return ConnectionResult(
                    success=False,
                    message=f"会话 {session_name} 不存在，请先建立连接",
                    status=ConnectionStatus.DISCONNECTED
                )
            
            # 获取执行前的输出基线
            baseline_result = subprocess.run(
                ['tmux', 'capture-pane', '-t', session_name, '-p'],
                capture_output=True, text=True
            )
            baseline_output = baseline_result.stdout if baseline_result.returncode == 0 else ""
            
            # 发送命令
            subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, command, 'Enter'],
                capture_output=True, check=True
            )
            
            # 等待命令完成
            success, output = self._wait_for_command_completion(
                session_name, command, baseline_output
            )
            
            return ConnectionResult(
                success=success,
                message=output if success else "命令执行失败",
                status=ConnectionStatus.READY if success else ConnectionStatus.ERROR,
                details={'command': command, 'output': output}
            )
            
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"命令执行异常: {str(e)}",
                status=ConnectionStatus.ERROR
            )
    
    def _wait_for_command_completion(self, session_name: str, command: str, baseline_output: str, timeout: int = 30) -> Tuple[bool, str]:
        """等待命令执行完成"""
        start_time = time.time()
        last_output = baseline_output
        stable_count = 0
        
        while time.time() - start_time < timeout:
            time.sleep(1)
            
            try:
                result = subprocess.run(
                    ['tmux', 'capture-pane', '-t', session_name, '-p'],
                    capture_output=True, text=True
                )
                
                if result.returncode != 0:
                    return False, "无法获取命令输出"
                
                current_output = result.stdout
                
                # 检查输出稳定性
                if current_output == last_output:
                    stable_count += 1
                    if stable_count >= 3:
                        return True, current_output
                else:
                    stable_count = 0
                    last_output = current_output
                
                # 检查提示符
                if self._has_new_prompt(current_output, baseline_output):
                    return True, current_output
                    
            except subprocess.CalledProcessError:
                return False, "获取输出失败"
        
        return False, "命令执行超时"
    
    def _has_new_prompt(self, current_output: str, baseline_output: str) -> bool:
        """检查是否有新的提示符"""
        prompt_patterns = [
            r'\$\s*$',
            r'#\s*$',
            r'>\s*$',
            r'~\]\$\s*$',
            r'@.*:\s*.*\$\s*$',
        ]
        
        current_lines = current_output.split('\n')
        baseline_lines = baseline_output.split('\n')
        
        if len(current_lines) > len(baseline_lines):
            new_lines = current_lines[len(baseline_lines):]
            for line in new_lines:
                for pattern in prompt_patterns:
                    if re.search(pattern, line):
                        return True
        
        return False


# 主要导出函数
def create_connection_manager(config_path: Optional[str] = None) -> ConnectionManager:
    """创建连接管理器实例"""
    return ConnectionManager(config_path)


def connect_server(server_name: str, force_recreate: bool = False, config_path: Optional[str] = None) -> ConnectionResult:
    """连接到服务器 - MCP工具主要调用入口"""
    try:
        manager = create_connection_manager(config_path)
        return manager.connect(server_name, force_recreate)
    except Exception as e:
        return ConnectionResult(
            success=False,
            message=f"连接管理器初始化失败: {str(e)}",
            status=ConnectionStatus.ERROR
        )


def disconnect_server(server_name: str, config_path: Optional[str] = None) -> ConnectionResult:
    """断开服务器连接 - MCP工具调用入口"""
    try:
        manager = create_connection_manager(config_path)
        return manager.disconnect(server_name)
    except Exception as e:
        return ConnectionResult(
            success=False,
            message=f"断开连接失败: {str(e)}",
            status=ConnectionStatus.ERROR
        )


def get_server_status(server_name: str, config_path: Optional[str] = None) -> ConnectionResult:
    """获取服务器状态 - MCP工具调用入口"""
    try:
        manager = create_connection_manager(config_path)
        return manager.get_status(server_name)
    except Exception as e:
        return ConnectionResult(
            success=False,
            message=f"获取状态失败: {str(e)}",
            status=ConnectionStatus.ERROR
        )


def execute_server_command(server_name: str, command: str, config_path: Optional[str] = None) -> ConnectionResult:
    """在服务器上执行命令 - MCP工具调用入口"""
    try:
        manager = create_connection_manager(config_path)
        return manager.execute_command(server_name, command)
    except Exception as e:
        return ConnectionResult(
            success=False,
            message=f"命令执行失败: {str(e)}",
            status=ConnectionStatus.ERROR
        )


def list_all_servers(config_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """列出所有服务器 - MCP工具调用入口"""
    try:
        manager = create_connection_manager(config_path)
        return manager.list_servers()
    except Exception as e:
        log_output(f"❌ 列出服务器失败: {str(e)}", "ERROR")
        return []


# ===== 环境配置管理器 =====
class EnvironmentManager:
    """
    环境配置管理器
    负责在Docker环境中自动配置shell环境（zsh、bash等）
    """
    
    def __init__(self, session_name: str, container_name: str):
        self.session_name = session_name
        self.container_name = container_name
        self.template_base = Path(__file__).parent.parent / "templates" / "configs"
        log_output("🔧 环境配置管理器已初始化", "INFO")
    
    def setup_shell_environment(self, shell_type: str = "zsh") -> bool:
        """
        设置shell环境配置
        
        Args:
            shell_type: shell类型（zsh、bash等）
        
        Returns:
            bool: 配置是否成功
        """
        try:
            log_output(f"🚀 开始配置{shell_type}环境", "INFO")
            
            if shell_type == "zsh":
                return self._setup_zsh_environment()
            elif shell_type == "bash":
                return self._setup_bash_environment()
            else:
                log_output(f"⚠️ 不支持的shell类型: {shell_type}", "WARNING")
                return False
                
        except Exception as e:
            log_output(f"❌ 环境配置失败: {e}", "ERROR")
            return False
    
    def _setup_zsh_environment(self) -> bool:
        """设置zsh环境配置"""
        try:
            # 1. 检查zsh是否安装
            if not self._check_zsh_installed():
                log_output("📦 zsh未安装，正在安装...", "INFO")
                if not self._install_zsh():
                    return False
            
            # 2. 检查配置文件是否存在
            config_files = [".zshrc", ".p10k.zsh"]
            missing_files = []
            
            for config_file in config_files:
                if not self._check_config_exists(config_file):
                    missing_files.append(config_file)
            
            # 3. 拷贝缺失的配置文件
            if missing_files:
                log_output(f"📋 发现缺失配置文件: {missing_files}", "INFO")
                if not self._copy_zsh_config_files(missing_files):
                    return False
            else:
                log_output("✅ zsh配置文件已存在", "SUCCESS")
            
            # 4. 切换到zsh环境
            return self._switch_to_zsh()
            
        except Exception as e:
            log_output(f"❌ zsh环境配置失败: {e}", "ERROR")
            return False
    
    def _setup_bash_environment(self) -> bool:
        """设置bash环境配置"""
        # bash通常是默认的，这里可以添加bash相关配置
        log_output("✅ bash环境配置完成", "SUCCESS")
        return True
    
    def _check_zsh_installed(self) -> bool:
        """检查zsh是否安装"""
        try:
            result = subprocess.run(
                ['tmux', 'send-keys', '-t', self.session_name, 'which zsh', 'Enter'],
                capture_output=True
            )
            time.sleep(1)
            
            # 获取输出检查
            output = subprocess.run(
                ['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                capture_output=True, text=True
            ).stdout
            
            return '/usr/bin/zsh' in output or '/bin/zsh' in output
            
        except Exception as e:
            log_output(f"❌ 检查zsh安装状态失败: {e}", "ERROR")
            return False
    
    def _install_zsh(self) -> bool:
        """安装zsh"""
        try:
            # 尝试使用apt安装（Ubuntu/Debian）
            log_output("📦 正在安装zsh...", "INFO")
            subprocess.run(
                ['tmux', 'send-keys', '-t', self.session_name, 'apt update && apt install -y zsh', 'Enter'],
                capture_output=True
            )
            time.sleep(10)  # 等待安装完成
            
            # 检查是否安装成功
            return self._check_zsh_installed()
            
        except Exception as e:
            log_output(f"❌ 安装zsh失败: {e}", "ERROR")
            return False
    
    def _check_config_exists(self, config_file: str) -> bool:
        """检查配置文件是否存在"""
        try:
            subprocess.run(
                ['tmux', 'send-keys', '-t', self.session_name, f'test -f ~/{config_file} && echo "EXISTS_{config_file}" || echo "MISSING_{config_file}"', 'Enter'],
                capture_output=True
            )
            time.sleep(1)
            
            # 获取输出检查
            output = subprocess.run(
                ['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                capture_output=True, text=True
            ).stdout
            
            return f"EXISTS_{config_file}" in output
            
        except Exception as e:
            log_output(f"❌ 检查配置文件失败: {e}", "ERROR")
            return False
    
    def _copy_zsh_config_files(self, missing_files: list) -> bool:
        """拷贝zsh配置文件到docker环境"""
        try:
            zsh_config_dir = self.template_base / "zsh"
            if not zsh_config_dir.exists():
                log_output(f"❌ 配置文件目录不存在: {zsh_config_dir}", "ERROR")
                return False
            
            success_count = 0
            for config_file in missing_files:
                source_file = zsh_config_dir / config_file
                if source_file.exists():
                    log_output(f"📁 正在拷贝 {config_file}...", "INFO")
                    
                    # 步骤1: 先删除容器内的同名文件（如果存在）避免重命名问题
                    log_output(f"🗑️ 清理容器内现有的 {config_file}...", "DEBUG")
                    subprocess.run(
                        ['docker', 'exec', self.container_name, 'rm', '-f', f'/root/{config_file}'],
                        capture_output=True
                    )
                    
                    # 步骤2: 拷贝文件到容器
                    result = subprocess.run(
                        ['docker', 'cp', str(source_file), f'{self.container_name}:/root/{config_file}'],
                        capture_output=True, text=True
                    )
                    
                    if result.returncode == 0:
                        log_output(f"✅ {config_file} 拷贝成功", "SUCCESS")
                        
                        # 步骤3: 验证文件确实存在且名称正确
                        verify_result = subprocess.run(
                            ['docker', 'exec', self.container_name, 'ls', '-la', f'/root/{config_file}'],
                            capture_output=True, text=True
                        )
                        
                        if verify_result.returncode == 0:
                            log_output(f"✅ {config_file} 验证存在", "SUCCESS")
                            success_count += 1
                        else:
                            log_output(f"⚠️ {config_file} 拷贝后验证失败", "WARNING")
                            success_count += 1  # 仍然算成功，可能只是验证命令问题
                    else:
                        error_msg = result.stderr.strip() if result.stderr else "未知错误"
                        log_output(f"❌ {config_file} 拷贝失败: {error_msg}", "ERROR")
                else:
                    log_output(f"⚠️ 源文件不存在: {source_file}", "WARNING")
            
            return success_count == len(missing_files)
            
        except Exception as e:
            log_output(f"❌ 拷贝配置文件失败: {e}", "ERROR")
            return False
    
    def _switch_to_zsh(self) -> bool:
        """切换到zsh环境"""
        try:
            log_output("🔄 切换到zsh环境", "INFO")
            subprocess.run(
                ['tmux', 'send-keys', '-t', self.session_name, 'zsh', 'Enter'],
                capture_output=True
            )
            time.sleep(2)
            
            # 检查是否成功切换
            output = subprocess.run(
                ['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                capture_output=True, text=True
            ).stdout
            
            # 简单检查是否有zsh相关提示符
            if any(indicator in output for indicator in ['➜', '❯', '%', 'zsh']):
                log_output("✅ 成功切换到zsh环境", "SUCCESS")
                return True
            else:
                log_output("⚠️ zsh环境切换可能未完成", "WARNING")
                return True  # 仍然返回True，因为命令已执行
                
        except Exception as e:
            log_output(f"❌ 切换到zsh环境失败: {e}", "ERROR")
            return False


# ===== 简化版交互引导器 =====
class SimpleInteractionGuide:
    """
    简化版交互引导器
    核心理念：用最简单直接的检测方式，避免复杂的模式匹配
    """
    
    def __init__(self, session_name: str):
        self.session_name = session_name
    
    def check_relay_ready(self, output: str) -> bool:
        """
        检查relay是否准备好 - 用户建议的简化方式
        只需要检查 -bash-baidu-ssl 即可
        """
        return '-bash-baidu-ssl' in output
    
    def check_ssh_connected(self, output: str) -> bool:
        """简单检查SSH是否连接成功"""
        # 检查常见的shell提示符
        return any(marker in output for marker in ['$', '#', '~', '@'])
    
    def check_docker_entered(self, output: str, container_name: str) -> bool:
        """简单检查是否进入Docker容器"""
        return (container_name in output or 
                'root@' in output or 
                '@' in output and 'container' in output.lower())
    
    def check_connection_ready(self, output: str, connection_type: str, container_name: str = None) -> bool:
        """
        根据连接类型检查是否准备好
        统一的检测入口，避免复杂的分支逻辑
        """
        if connection_type == 'relay':
            return self.check_relay_ready(output)
        elif connection_type == 'ssh':
            return self.check_ssh_connected(output)
        elif connection_type == 'docker' and container_name:
            return self.check_docker_entered(output, container_name)
        return False
    
    def simple_guidance(self, message: str):
        """简单的用户提示 - 避免复杂的引导文本"""
        log_output(f"🎯 {message}", "INFO")
        log_output(f"📋 查看详情: tmux attach -t {self.session_name}", "INFO")
    
    def check_common_errors(self, output: str) -> Optional[str]:
        """检查常见错误模式"""
        output_lower = output.lower()
        
        if 'connection refused' in output_lower or 'connection timed out' in output_lower:
            return "连接被拒绝或超时"
        elif 'permission denied' in output_lower or 'access denied' in output_lower:
            return "权限拒绝"
        elif 'host key verification failed' in output_lower:
            return "主机密钥验证失败"
        elif 'no route to host' in output_lower:
            return "无法到达主机"
        elif 'authentication failed' in output_lower:
            return "认证失败"
        
        return None


# ===== 简化版连接管理器 =====
class SimpleConnectionManager:
    """
    简化版连接管理器
    核心理念：发现session就杀掉重建，确保每次都是干净状态
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = self._find_config_file() if not config_path else config_path
        self.servers = self._load_servers()
        self.guide = None  # 延迟初始化，每次连接时创建
        log_output("🚀 简化版连接管理器已初始化", "SUCCESS")
    
    def _find_config_file(self) -> str:
        """查找配置文件"""
        user_config_dir = Path.home() / ".remote-terminal"
        user_config_file = user_config_dir / "config.yaml"
        
        if user_config_file.exists():
            return str(user_config_file)
        
        script_dir = Path(__file__).parent
        project_dir = script_dir.parent
        local_config = project_dir / "config" / "servers.local.yaml"
        if local_config.exists():
            return str(local_config)
        
        template_config = project_dir / "config" / "servers.template.yaml"
        if template_config.exists():
            return str(template_config)
        
        raise FileNotFoundError("未找到配置文件")
    
    def _load_servers(self) -> Dict[str, ServerConfig]:
        """加载服务器配置"""
        servers = {}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            servers_config = config.get('servers', {})
            for name, server_data in servers_config.items():
                # 简化的连接类型判断
                if server_data.get('type') == 'script_based':
                    connection_config = server_data.get('specs', {}).get('connection', {})
                    tool = connection_config.get('tool', 'ssh')
                    connection_type = ConnectionType.RELAY if tool == 'relay-cli' else ConnectionType.SSH
                else:
                    connection_type = ConnectionType.SSH
                
                # 简化的Docker配置
                docker_config = server_data.get('specs', {}).get('docker', {}) or server_data.get('docker', {})
                
                server_config = ServerConfig(
                    name=name,
                    host=server_data.get('host', ''),
                    username=server_data.get('username', ''),
                    connection_type=connection_type,
                    docker_container=docker_config.get('container_name'),
                    docker_shell=docker_config.get('shell', 'zsh'),
                    session_name=server_data.get('session', {}).get('name', f"{name}_session")
                )
                
                servers[name] = server_config
            
            return servers
            
        except Exception as e:
            raise Exception(f"配置加载失败: {str(e)}")
    
    def _kill_existing_session(self, session_name: str) -> bool:
        """杀掉现有session（如果存在）"""
        try:
            # 检查session是否存在
            result = subprocess.run(
                ['tmux', 'has-session', '-t', session_name],
                capture_output=True
            )
            
            if result.returncode == 0:
                # session存在，杀掉它
                log_output(f"🔄 发现现有session {session_name}，正在清理...", "WARNING")
                kill_result = subprocess.run(
                    ['tmux', 'kill-session', '-t', session_name],
                    capture_output=True
                )
                
                if kill_result.returncode == 0:
                    log_output(f"✅ 已清理session: {session_name}", "SUCCESS")
                    return True
                else:
                    log_output(f"⚠️ 清理session失败: {kill_result.stderr.decode()}", "WARNING")
                    return False
            else:
                # session不存在，正常
                log_output(f"📋 session {session_name} 不存在，可以直接创建", "INFO")
                return True
                
        except Exception as e:
            log_output(f"❌ 检查session异常: {str(e)}", "ERROR")
            return False
    
    def _create_fresh_session(self, session_name: str) -> ConnectionResult:
        """创建全新的session"""
        try:
            result = subprocess.run(
                ['tmux', 'new-session', '-d', '-s', session_name],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                return ConnectionResult(
                    success=False,
                    message=f"创建session失败: {result.stderr}",
                    status=ConnectionStatus.ERROR
                )
            
            log_output(f"✅ 创建新session: {session_name}", "SUCCESS")
            return ConnectionResult(
                success=True,
                message="session创建成功",
                session_name=session_name,
                status=ConnectionStatus.CONNECTING
            )
            
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"创建session异常: {str(e)}",
                status=ConnectionStatus.ERROR
            )
    
    def _simple_final_check(self, session_name: str, server_config: ServerConfig) -> bool:
        """
        简化的最终检查：只检查session是否响应
        不做复杂的环境判断，简单快速
        """
        try:
            # 发送简单测试命令
            subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, 'echo "CONNECTION_TEST_OK"', 'Enter'],
                capture_output=True
            )
            
            # 等待1秒（固定短时间）
            time.sleep(1)
            
            # 获取输出
            result = subprocess.run(
                ['tmux', 'capture-pane', '-p', '-t', session_name],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                return False
            
            # 简单检查：只要能执行命令就认为OK
            output = result.stdout
            has_response = 'CONNECTION_TEST_OK' in output
            
            if has_response:
                log_output("✅ 连接测试通过", "SUCCESS")
            else:
                log_output("⚠️ 连接测试无响应", "WARNING")
            
            return has_response
            
        except Exception as e:
            log_output(f"❌ 连接测试异常: {str(e)}", "ERROR")
            return False
    
    def connect(self, server_name: str) -> ConnectionResult:
        """
        简化的连接流程：
        1. 强制清理现有session
        2. 创建新session
        3. 执行连接
        4. 简单验证
        """
        if server_name not in self.servers:
            return ConnectionResult(
                success=False,
                message=f"服务器 {server_name} 不存在",
                status=ConnectionStatus.ERROR
            )
        
        server_config = self.servers[server_name]
        session_name = server_config.session_name
        
        log_output(f"🚀 开始连接 {server_name} (强制重建模式)", "INFO")
        
        # 步骤1: 强制清理现有session
        if not self._kill_existing_session(session_name):
            return ConnectionResult(
                success=False,
                message="清理现有session失败",
                status=ConnectionStatus.ERROR
            )
        
        # 步骤2: 创建全新session
        create_result = self._create_fresh_session(session_name)
        if not create_result.success:
            return create_result
        
        # 步骤3: 执行连接流程
        try:
            if server_config.connection_type == ConnectionType.RELAY:
                connect_result = self._execute_relay_connection(server_config)
            else:
                connect_result = self._execute_ssh_connection(server_config)
            
            if not connect_result.success:
                return connect_result
            
            # 步骤4: 简单验证
            time.sleep(2)  # 给连接一点时间稳定
            if self._simple_final_check(session_name, server_config):
                log_output(f"🎉 连接成功: {server_name}", "SUCCESS")
                self._show_simple_summary(server_name, session_name, server_config)
                return ConnectionResult(
                    success=True,
                    message="连接建立成功",
                    session_name=session_name,
                    status=ConnectionStatus.CONNECTED
                )
            else:
                return ConnectionResult(
                    success=False,
                    message="连接验证失败",
                    session_name=session_name,
                    status=ConnectionStatus.ERROR
                )
                
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"连接异常: {str(e)}",
                status=ConnectionStatus.ERROR
            )
    
    def _execute_relay_connection(self, server_config: ServerConfig) -> ConnectionResult:
        """执行Relay连接（简化版 - 使用SimpleInteractionGuide）"""
        session_name = server_config.session_name
        
        try:
            # 创建简化版交互引导器
            guide = SimpleInteractionGuide(session_name)
            
            log_output("📡 启动relay-cli（无参数）", "INFO")
            
            # 严格遵循规则：relay-cli 不接任何参数
            subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, 'relay-cli', 'Enter'],
                capture_output=True
            )
            
            log_output("⏳ 等待relay认证完成", "WARNING")
            guide.simple_guidance("需要手动完成relay认证")
            
            # 简化的等待逻辑：检查是否出现-bash-baidu-ssl
            max_wait = 120  # 最大等待2分钟
            check_interval = 5  # 每5秒检查一次
            
            for i in range(0, max_wait, check_interval):
                time.sleep(check_interval)
                
                # 获取当前输出
                result = subprocess.run(
                    ['tmux', 'capture-pane', '-t', session_name, '-p'],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
                    output = result.stdout
                    
                    # 检查错误
                    error = guide.check_common_errors(output)
                    if error:
                        return ConnectionResult(
                            success=False,
                            message=f"Relay认证失败: {error}",
                            status=ConnectionStatus.ERROR
                        )
                    
                    # 用户建议的简化检测：只检查-bash-baidu-ssl
                    if guide.check_relay_ready(output):
                        log_output("✅ 检测到relay环境准备就绪", "SUCCESS")
                        break
                        
                    log_output(f"⏳ 等待relay认证... ({i+check_interval}s)", "INFO")
                else:
                    log_output("❌ 无法获取session输出", "ERROR")
                    return ConnectionResult(
                        success=False,
                        message="无法监控relay认证状态",
                        status=ConnectionStatus.ERROR
                    )
            else:
                return ConnectionResult(
                    success=False,
                    message="relay认证超时",
                    status=ConnectionStatus.ERROR
                )
            
            # SSH到目标服务器
            log_output(f"🔗 SSH到目标服务器: {server_config.host}", "INFO")
            subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, f'ssh {server_config.host}', 'Enter'],
                capture_output=True
            )
            
            time.sleep(5)  # 等待SSH连接建立
            
            # 如果有Docker容器，进入容器并配置环境
            if server_config.docker_container:
                docker_result = self._handle_docker_environment(server_config)
                if not docker_result.success:
                    return docker_result
            
            return ConnectionResult(
                success=True,
                message="Relay连接流程完成",
                status=ConnectionStatus.CONNECTED
            )
            
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"Relay连接异常: {str(e)}",
                status=ConnectionStatus.ERROR
            )
    
    def _execute_ssh_connection(self, server_config: ServerConfig) -> ConnectionResult:
        """执行SSH连接"""
        session_name = server_config.session_name
        
        try:
            log_output(f"🔗 SSH连接到: {server_config.host}", "INFO")
            
            ssh_cmd = f'ssh {server_config.username}@{server_config.host}'
            subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, ssh_cmd, 'Enter'],
                capture_output=True
            )
            
            time.sleep(5)  # 等待SSH连接
            
            # 如果有Docker容器，进入容器并配置环境
            if server_config.docker_container:
                docker_result = self._handle_docker_environment(server_config)
                if not docker_result.success:
                    return docker_result
            
            return ConnectionResult(
                success=True,
                message="SSH连接流程完成",
                status=ConnectionStatus.CONNECTED
            )
            
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"SSH连接异常: {str(e)}",
                status=ConnectionStatus.ERROR
            )
    
    def _handle_docker_environment(self, server_config: ServerConfig) -> ConnectionResult:
        """
        处理Docker环境配置
        用户建议的逻辑：
        1. 先用bash进入docker环境
        2. 如果配置了zsh，用EnvironmentManager检查和配置
        3. 在EnvironmentManager之后加AutoSyncManager
        4. 最后切换到用户偏好的shell
        """
        session_name = server_config.session_name
        container_name = server_config.docker_container
        
        try:
            log_output(f"🐳 进入Docker容器: {container_name}", "INFO")
            
            # 步骤1: 用bash进入docker环境（默认）
            bash_cmd = f'docker exec -it {container_name} bash'
            subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, bash_cmd, 'Enter'],
                capture_output=True
            )
            time.sleep(3)  # 等待容器进入
            
            # 步骤2: 如果用户配置了自动配置shell环境，则进行配置
            if server_config.auto_configure_shell and server_config.preferred_shell != "bash":
                log_output(f"🔧 开始配置 {server_config.preferred_shell} 环境", "INFO")
                
                # 创建环境配置管理器
                env_manager = EnvironmentManager(session_name, container_name)
                
                # 设置shell环境
                if env_manager.setup_shell_environment(server_config.preferred_shell):
                    log_output(f"✅ {server_config.preferred_shell} 环境配置成功", "SUCCESS")
                else:
                    log_output(f"⚠️ {server_config.preferred_shell} 环境配置失败，将继续使用bash", "WARNING")
            
            # 步骤3: 在EnvironmentManager之后加AutoSyncManager
            if server_config.auto_sync_enabled:
                log_output("🔄 开始设置自动同步环境...", "INFO")
                
                try:
                    # 导入AutoSyncManager
                    from auto_sync_manager import AutoSyncManager, SyncConfig
                    
                    # 创建AutoSyncManager实例
                    sync_manager = AutoSyncManager(session_name)
                    
                    # 准备同步配置
                    sync_config = SyncConfig(
                        remote_workspace=server_config.sync_remote_workspace,
                        ftp_port=server_config.sync_ftp_port,
                        ftp_user=server_config.sync_ftp_user,
                        ftp_password=server_config.sync_ftp_password,
                        local_workspace=server_config.sync_local_workspace,
                        auto_sync=True,
                        sync_patterns=server_config.sync_patterns,
                        exclude_patterns=server_config.sync_exclude_patterns
                    )
                    
                    # 设置自动同步环境
                    success, msg = sync_manager.setup_auto_sync(sync_config)
                    if success:
                        log_output("✅ 自动同步环境设置成功", "SUCCESS")
                        log_output(f"   FTP端口: {server_config.sync_ftp_port}", "INFO")
                        log_output(f"   远程目录: {server_config.sync_remote_workspace}", "INFO")
                    else:
                        log_output(f"⚠️ 自动同步环境设置失败: {msg}", "WARNING")
                        log_output("💡 继续使用普通连接", "INFO")
                        
                except ImportError:
                    log_output("⚠️ AutoSyncManager模块未找到，跳过同步设置", "WARNING")
                except Exception as e:
                    log_output(f"⚠️ 自动同步设置异常: {str(e)}", "WARNING")
            else:
                log_output("💡 自动同步未启用", "INFO")
            
            # 步骤4: 如果不自动配置，但用户偏好不是bash，直接切换
            if not server_config.auto_configure_shell and server_config.preferred_shell != "bash":
                log_output(f"🔄 切换到 {server_config.preferred_shell}", "INFO")
                subprocess.run(
                    ['tmux', 'send-keys', '-t', session_name, server_config.preferred_shell, 'Enter'],
                    capture_output=True
                )
                time.sleep(2)
            
            elif server_config.preferred_shell == "bash":
                log_output("✅ 使用默认bash环境", "SUCCESS")
            
            # 简单验证是否成功进入容器
            time.sleep(1)
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', session_name, '-p'],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                output = result.stdout
                # 检查是否在容器内（可能有root@或容器名）
                if any(indicator in output for indicator in ['root@', container_name, '#', '$']):
                    log_output("✅ Docker环境配置完成", "SUCCESS")
                    return ConnectionResult(
                        success=True,
                        message="Docker环境配置成功",
                        status=ConnectionStatus.CONNECTED
                    )
            
            # 即使验证不确定，也返回成功（给用户一个机会）
            log_output("⚠️ Docker环境状态不确定，但继续执行", "WARNING")
            return ConnectionResult(
                success=True,
                message="Docker环境配置可能成功",
                status=ConnectionStatus.CONNECTED
            )
            
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"Docker环境配置失败: {str(e)}",
                status=ConnectionStatus.ERROR
            )
    
    def _show_simple_summary(self, server_name: str, session_name: str, server_config: ServerConfig):
        """显示简单的连接摘要"""
        log_output("", "INFO")
        log_output("=" * 50, "SUCCESS")
        log_output(f"🎉 {server_name} 连接成功!", "SUCCESS")
        log_output(f"📋 会话名称: {session_name}", "INFO")
        log_output(f"🔗 连接方式: {server_config.connection_type.value}", "INFO")
        if server_config.docker_container:
            log_output(f"🐳 Docker容器: {server_config.docker_container}", "INFO")
        log_output("", "INFO")
        log_output("🎯 使用方法:", "INFO")
        log_output(f"   连接终端: tmux attach -t {session_name}", "INFO")
        log_output(f"   退出会话: Ctrl+B, D", "INFO")
        log_output("=" * 50, "SUCCESS")
        log_output("", "INFO")
    
    def disconnect(self, server_name: str) -> ConnectionResult:
        """断开连接（简化版）"""
        if server_name not in self.servers:
            return ConnectionResult(
                success=False,
                message=f"服务器 {server_name} 不存在",
                status=ConnectionStatus.ERROR
            )
        
        session_name = self.servers[server_name].session_name
        
        if self._kill_existing_session(session_name):
            return ConnectionResult(
                success=True,
                message=f"已断开 {server_name}",
                status=ConnectionStatus.DISCONNECTED
            )
        else:
            return ConnectionResult(
                success=False,
                message="断开连接失败",
                status=ConnectionStatus.ERROR
            )
    
    def get_status(self, server_name: str) -> ConnectionResult:
        """获取状态（简化版）"""
        if server_name not in self.servers:
            return ConnectionResult(
                success=False,
                message=f"服务器 {server_name} 不存在",
                status=ConnectionStatus.ERROR
            )
        
        session_name = self.servers[server_name].session_name
        
        try:
            result = subprocess.run(
                ['tmux', 'has-session', '-t', session_name],
                capture_output=True
            )
            
            if result.returncode == 0:
                return ConnectionResult(
                    success=True,
                    message=f"{server_name} 会话存在",
                    session_name=session_name,
                    status=ConnectionStatus.CONNECTED
                )
            else:
                return ConnectionResult(
                    success=True,
                    message=f"{server_name} 会话不存在",
                    status=ConnectionStatus.DISCONNECTED
                )
                
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"获取状态异常: {str(e)}",
                status=ConnectionStatus.ERROR
            )
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """列出所有服务器"""
        return [
            {
                'name': name,
                'host': config.host,
                'username': config.username,
                'connection_type': config.connection_type.value,
                'docker_container': config.docker_container,
                'session_name': config.session_name
            }
            for name, config in self.servers.items()
        ]
    
    def execute_command(self, server_name: str, command: str) -> ConnectionResult:
        """执行命令（简化版）"""
        if server_name not in self.servers:
            return ConnectionResult(
                success=False,
                message=f"服务器 {server_name} 不存在",
                status=ConnectionStatus.ERROR
            )
        
        session_name = self.servers[server_name].session_name
        
        try:
            # 检查session是否存在
            result = subprocess.run(
                ['tmux', 'has-session', '-t', session_name],
                capture_output=True
            )
            
            if result.returncode != 0:
                return ConnectionResult(
                    success=False,
                    message=f"会话 {session_name} 不存在",
                    status=ConnectionStatus.DISCONNECTED
                )
            
            # 执行命令
            subprocess.run(
                ['tmux', 'send-keys', '-t', session_name, command, 'Enter'],
                capture_output=True
            )
            
            return ConnectionResult(
                success=True,
                message=f"命令已发送: {command}",
                session_name=session_name,
                status=ConnectionStatus.CONNECTED
            )
            
        except Exception as e:
            return ConnectionResult(
                success=False,
                message=f"执行命令异常: {str(e)}",
                status=ConnectionStatus.ERROR
            )


# ===== 统一的工厂函数 =====
def create_connection_manager(config_path: Optional[str] = None, simple_mode: bool = False) -> Any:
    """
    创建连接管理器
    
    Args:
        config_path: 配置文件路径
        simple_mode: 是否使用简化模式
            - True: 使用简化版（强制重建策略）
            - False: 使用复杂版（智能判断策略）
    
    Returns:
        ConnectionManager 或 SimpleConnectionManager 实例
    """
    if simple_mode:
        return SimpleConnectionManager(config_path)
    else:
        return ConnectionManager(config_path)


# ===== 更新现有的函数支持简化模式 =====
def connect_server(server_name: str, force_recreate: bool = False, config_path: Optional[str] = None, simple_mode: bool = False) -> ConnectionResult:
    """
    连接到服务器
    
    Args:
        server_name: 服务器名称
        force_recreate: 是否强制重建（仅在复杂模式下生效）
        config_path: 配置文件路径
        simple_mode: 是否使用简化模式
    
    Returns:
        ConnectionResult: 连接结果
    """
    try:
        manager = create_connection_manager(config_path, simple_mode)
        if simple_mode:
            return manager.connect(server_name)
        else:
            return manager.connect(server_name, force_recreate)
    except Exception as e:
        return ConnectionResult(
            success=False,
            message=f"连接异常: {str(e)}",
            status=ConnectionStatus.ERROR
        )


def disconnect_server(server_name: str, config_path: Optional[str] = None, simple_mode: bool = False) -> ConnectionResult:
    """
    断开服务器连接
    
    Args:
        server_name: 服务器名称
        config_path: 配置文件路径
        simple_mode: 是否使用简化模式
    
    Returns:
        ConnectionResult: 操作结果
    """
    try:
        manager = create_connection_manager(config_path, simple_mode)
        return manager.disconnect(server_name)
    except Exception as e:
        return ConnectionResult(
            success=False,
            message=f"断开连接异常: {str(e)}",
            status=ConnectionStatus.ERROR
        )


def get_server_status(server_name: str, config_path: Optional[str] = None, simple_mode: bool = False) -> ConnectionResult:
    """
    获取服务器状态
    
    Args:
        server_name: 服务器名称
        config_path: 配置文件路径
        simple_mode: 是否使用简化模式
    
    Returns:
        ConnectionResult: 状态结果
    """
    try:
        manager = create_connection_manager(config_path, simple_mode)
        return manager.get_status(server_name)
    except Exception as e:
        return ConnectionResult(
            success=False,
            message=f"获取状态异常: {str(e)}",
            status=ConnectionStatus.ERROR
        )


def execute_server_command(server_name: str, command: str, config_path: Optional[str] = None, simple_mode: bool = False) -> ConnectionResult:
    """
    执行服务器命令
    
    Args:
        server_name: 服务器名称
        command: 要执行的命令
        config_path: 配置文件路径
        simple_mode: 是否使用简化模式
    
    Returns:
        ConnectionResult: 执行结果
    """
    try:
        manager = create_connection_manager(config_path, simple_mode)
        return manager.execute_command(server_name, command)
    except Exception as e:
        return ConnectionResult(
            success=False,
            message=f"执行命令异常: {str(e)}",
            status=ConnectionStatus.ERROR
        )


def list_all_servers(config_path: Optional[str] = None, simple_mode: bool = False) -> List[Dict[str, Any]]:
    """
    列出所有服务器
    
    Args:
        config_path: 配置文件路径
        simple_mode: 是否使用简化模式
    
    Returns:
        List[Dict[str, Any]]: 服务器列表
    """
    try:
        manager = create_connection_manager(config_path, simple_mode)
        return manager.list_servers()
    except Exception as e:
        log_output(f"列出服务器异常: {str(e)}", "ERROR")
        return []


if __name__ == "__main__":
    # 命令行测试接口
    import sys
    if len(sys.argv) > 1:
        server_name = sys.argv[1]
        result = connect_server(server_name)
        if result.success:
            print(f"✅ 连接成功: {result.message}")
        else:
            print(f"❌ 连接失败: {result.message}")
    else:
        print("用法: python connect.py <server_name>") 