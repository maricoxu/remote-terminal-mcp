#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
增强版SSH连接管理器 - 用户体验优化版本

主要改进：
1. 智能连接检测和自动修复
2. 更清晰的用户反馈
3. 一键式Docker环境连接
4. 渐进式错误恢复
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
import asyncio
from concurrent.futures import ThreadPoolExecutor


def log_output(message, level="INFO"):
    """增强的日志输出，带级别标识"""
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


@dataclass
class ConnectionState:
    """连接状态跟踪"""
    server_name: str
    session_name: str
    stage: str  # "initializing", "connecting", "docker_setup", "ready", "failed"
    progress: int  # 0-100
    message: str
    last_update: float
    auto_recovery: bool = True


class InteractiveGuide:
    """智能交互引导系统"""
    
    def __init__(self, session_name: str):
        self.session_name = session_name
        self.interaction_patterns = {
            'password': [
                r'password:',
                r'请输入密码',
                r'Enter password',
                r'Password for'
            ],
            'fingerprint': [
                r'fingerprint',
                r'ECDSA key fingerprint',
                r'RSA key fingerprint',
                r'\(yes/no\)',
                r'Are you sure you want to continue connecting'
            ],
            'confirmation': [
                r'\(y/n\)',
                r'\(yes/no\)',
                r'Continue\?',
                r'Proceed\?'
            ],
            'token': [
                r'token:',
                r'verification code',
                r'authenticator',
                r'2FA'
            ]
        }
    
    def detect_input_needed(self, output: str) -> Optional[str]:
        """检测需要的输入类型"""
        output_lower = output.lower()
        
        for input_type, patterns in self.interaction_patterns.items():
            for pattern in patterns:
                if re.search(pattern, output_lower):
                    return input_type
        
        return None
    
    def guide_user_input(self, input_type: str, output: str) -> Dict[str, Any]:
        """生成用户输入引导信息"""
        guides = {
            'password': {
                'title': '🔐 需要输入密码',
                'description': '系统需要您输入密码以继续连接',
                'instructions': [
                    f'1. 打开新终端窗口',
                    f'2. 执行: tmux attach -t {self.session_name}',
                    f'3. 在提示符处输入密码',
                    f'4. 输入完成后按 Ctrl+B, D 退出会话',
                    f'5. 系统将自动继续连接流程'
                ],
                'timeout': 300,  # 5分钟超时
                'auto_continue': True
            },
            'fingerprint': {
                'title': '🔑 需要确认服务器指纹',
                'description': '首次连接此服务器，需要确认安全指纹',
                'instructions': [
                    f'1. 打开新终端窗口',
                    f'2. 执行: tmux attach -t {self.session_name}',
                    f'3. 查看显示的指纹信息',
                    f'4. 输入 "yes" 确认连接',
                    f'5. 输入完成后按 Ctrl+B, D 退出会话'
                ],
                'timeout': 120,  # 2分钟超时
                'auto_continue': True
            },
            'confirmation': {
                'title': '✅ 需要确认操作',
                'description': '系统需要您确认一个操作',
                'instructions': [
                    f'1. 打开新终端窗口',
                    f'2. 执行: tmux attach -t {self.session_name}',
                    f'3. 查看提示信息',
                    f'4. 输入 "y" 或 "yes" 确认',
                    f'5. 输入完成后按 Ctrl+B, D 退出会话'
                ],
                'timeout': 60,   # 1分钟超时
                'auto_continue': True
            },
            'token': {
                'title': '🛡️ 需要输入验证码',
                'description': '系统需要二次验证码（2FA/令牌）',
                'instructions': [
                    f'1. 打开您的验证器应用',
                    f'2. 获取当前验证码',
                    f'3. 打开新终端: tmux attach -t {self.session_name}',
                    f'4. 输入6位验证码',
                    f'5. 输入完成后按 Ctrl+B, D 退出会话'
                ],
                'timeout': 180,  # 3分钟超时
                'auto_continue': True
            }
        }
        
        return guides.get(input_type, {
            'title': '⌨️ 需要手动输入',
            'description': '系统需要您手动输入信息',
            'instructions': [
                f'1. 打开新终端窗口',
                f'2. 执行: tmux attach -t {self.session_name}',
                f'3. 查看提示并输入相应信息',
                f'4. 输入完成后按 Ctrl+B, D 退出会话'
            ],
            'timeout': 300,
            'auto_continue': True
        })


class EnhancedSSHManager:
    """增强版SSH管理器 - 专注用户体验"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化增强版SSH管理器"""
        self.connection_states: Dict[str, ConnectionState] = {}
        self.auto_recovery_enabled = True
        self.connection_timeout = 60  # 增加超时时间
        self.interactive_guides: Dict[str, InteractiveGuide] = {}
        
        # 直接集成配置加载逻辑，不再依赖base_manager
        self.servers: Dict[str, Any] = {}
        self.global_settings: Dict[str, Any] = {}
        self.security_settings: Dict[str, Any] = {}
        
        # 查找并加载配置文件
        self.config_path = self._find_config_file() if config_path is None else config_path
        self._load_config()
        
        log_output("🚀 Enhanced SSH Manager 已启动", "SUCCESS")
        log_output("💡 新功能: 智能连接检测、自动Docker环境、一键恢复、交互引导", "INFO")
    
    def _find_config_file(self) -> str:
        """查找配置文件"""
        # 1. 用户目录配置
        user_config_dir = Path.home() / ".remote-terminal-mcp"
        user_config_file = user_config_dir / "config.yaml"
        
        if user_config_file.exists():
            return str(user_config_file)
        
        # 2. 项目本地配置
        script_dir = Path(__file__).parent
        project_dir = script_dir.parent
        local_config = project_dir / "config" / "servers.local.yaml"
        if local_config.exists():
            return str(local_config)
        
        # 3. 模板配置
        template_config = project_dir / "config" / "servers.template.yaml"
        if template_config.exists():
            return str(template_config)
        
        raise FileNotFoundError("未找到配置文件")
    
    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 解析服务器配置
            servers_config = config.get('servers', {})
            for server_name, server_config in servers_config.items():
                # 构建specs字典
                specs = server_config.get('specs', {})
                
                # 如果是script_based类型，将connection、docker等配置放入specs
                if server_config.get('type') == 'script_based':
                    if 'connection' in server_config:
                        specs['connection'] = server_config['connection']
                    if 'docker' in server_config:
                        specs['docker'] = server_config['docker']
                    if 'bos' in server_config:
                        specs['bos'] = server_config['bos']
                    if 'environment_setup' in server_config:
                        specs['environment_setup'] = server_config['environment_setup']
                
                # 创建服务器对象
                server_obj = type('ServerConfig', (), {
                    'name': server_name,
                    'type': server_config.get('type', 'direct_ssh'),
                    'host': server_config.get('host', ''),
                    'port': server_config.get('port', 22),
                    'username': server_config.get('username', ''),
                    'private_key_path': server_config.get('private_key_path', ''),
                    'description': server_config.get('description', ''),
                    'specs': specs,
                    'session': server_config.get('session'),
                    'jump_host': server_config.get('jump_host'),
                    'password': server_config.get('password')
                })()
                
                self.servers[server_name] = server_obj
            
            # 加载全局设置
            self.global_settings = config.get('global_settings', {})
            self.security_settings = config.get('security_settings', {})
            
        except Exception as e:
            raise Exception(f"配置文件解析失败: {str(e)}")
    
    def get_server(self, server_name: str):
        """获取服务器配置"""
        return self.servers.get(server_name)
    
    def list_servers_internal(self) -> List[Dict[str, Any]]:
        """列出所有服务器"""
        servers_info = []
        for server_name, server in self.servers.items():
            server_info = {
                'name': server_name,
                'host': server.host,
                'description': server.description,
                'type': server.type,
                'specs': server.specs or {}
            }
            
            if hasattr(server, 'jump_host') and server.jump_host:
                server_info['jump_host'] = server.jump_host['host']
            
            servers_info.append(server_info)
        
        return servers_info
    
    def execute_command_internal(self, server_name: str, command: str) -> Tuple[bool, str]:
        """执行命令的内部实现"""
        server = self.get_server(server_name)
        if not server:
            return False, f"服务器 {server_name} 不存在"
        
        # 对于script_based类型，使用tmux会话执行
        if server.type == 'script_based':
            session_name = server.session.get('name', f"{server_name}_session") if server.session else f"{server_name}_session"
            
            try:
                # 检查会话是否存在
                check_result = subprocess.run(['tmux', 'has-session', '-t', session_name], 
                                            capture_output=True)
                
                if check_result.returncode != 0:
                    return False, f"会话 {session_name} 不存在，请先建立连接"
                
                # 发送命令
                subprocess.run(['tmux', 'send-keys', '-t', session_name, command, 'Enter'], 
                             capture_output=True)
                
                # 等待执行完成
                time.sleep(2)
                
                # 获取输出
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                return True, result.stdout if result.returncode == 0 else "命令执行完成"
                
            except Exception as e:
                return False, f"命令执行失败: {str(e)}"
        else:
            return False, f"不支持的服务器类型: {server.type}"
    
    def smart_connect(self, server_name: str, force_recreate: bool = False) -> Tuple[bool, str]:
        """
        智能连接 - 核心用户体验优化方法
        
        特性：
        1. 自动检测连接状态
        2. 智能Docker环境设置
        3. 渐进式错误恢复
        4. 实时进度反馈
        """
        server = self.get_server(server_name)
        if not server:
            return False, f"服务器 {server_name} 不存在"
        
        session_name = server.session.get('name', f"{server_name}_dev") if server.session else f"{server_name}_dev"
        
        # 初始化连接状态
        self.connection_states[server_name] = ConnectionState(
            server_name=server_name,
            session_name=session_name,
            stage="initializing",
            progress=0,
            message="开始智能连接流程...",
            last_update=time.time()
        )
        
        try:
            # 阶段1: 智能连接检测
            self._update_progress(server_name, 10, "检测现有连接状态...")
            
            if not force_recreate:
                existing_status = self._detect_existing_connection(server_name, session_name)
                if existing_status == "ready":
                    self._update_progress(server_name, 100, "连接已就绪！")
                    return True, f"连接已存在且正常: {session_name}"
                elif existing_status == "recoverable":
                    log_output("🔄 检测到可恢复的连接，正在修复...", "WARNING")
                    success = self._recover_connection(server_name, session_name)
                    if success:
                        self._update_progress(server_name, 100, "连接已恢复！")
                        return True, f"连接已恢复: {session_name}"
            
            # 阶段2: 建立新连接
            self._update_progress(server_name, 20, "建立新连接...")
            success, msg = self._establish_smart_connection(server, session_name)
            if not success:
                self._update_progress(server_name, 0, f"连接失败: {msg}")
                return False, msg
            
            # 阶段3: Docker环境设置
            if server.specs and server.specs.get('docker'):
                self._update_progress(server_name, 60, "设置Docker环境...")
                success, msg = self._setup_docker_environment(server, session_name)
                if not success:
                    log_output(f"Docker设置失败: {msg}", "WARNING")
                    log_output("💡 继续使用主机环境", "INFO")
            
            # 阶段4: 环境验证
            self._update_progress(server_name, 90, "验证环境...")
            success = self._verify_environment(session_name)
            if not success:
                return False, "环境验证失败"
            
            # 完成
            self._update_progress(server_name, 100, "连接已就绪！")
            
            # 显示连接信息
            self._show_connection_info(server_name, session_name)
            
            return True, f"智能连接完成: {session_name}"
            
        except Exception as e:
            self._update_progress(server_name, 0, f"连接异常: {str(e)}")
            return False, f"智能连接失败: {str(e)}"
    
    def _detect_existing_connection(self, server_name: str, session_name: str) -> str:
        """
        智能检测现有连接状态
        返回: "ready", "recoverable", "failed", "none"
        """
        try:
            # 检查tmux会话是否存在
            check_result = subprocess.run(['tmux', 'has-session', '-t', session_name], 
                                        capture_output=True)
            
            if check_result.returncode != 0:
                return "none"
            
            # 发送测试命令
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          'echo "CONNECTION_TEST_$(date +%s)"', 'Enter'], 
                         capture_output=True)
            time.sleep(2)
            
            # 获取输出
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                return "failed"
            
            output = result.stdout
            
            # 分析连接状态
            if 'CONNECTION_TEST_' in output:
                # 检查是否在远程环境
                if any(local_indicator in output for local_indicator in 
                       ['MacBook-Pro', 'localhost', 'xuyehua@MacBook']):
                    return "recoverable"  # 会话存在但回到本地
                else:
                    return "ready"  # 连接正常
            else:
                return "recoverable"  # 会话无响应但可能恢复
                
        except Exception as e:
            log_output(f"连接检测失败: {str(e)}", "ERROR")
            return "failed"
    
    def _recover_connection(self, server_name: str, session_name: str) -> bool:
        """智能连接恢复"""
        try:
            log_output("🔧 开始智能恢复流程...", "INFO")
            
            # 清理异常会话
            subprocess.run(['tmux', 'kill-session', '-t', session_name], capture_output=True)
            time.sleep(1)
            
            # 重新建立连接
            server = self.get_server(server_name)
            if not server:
                return False
            
            success, msg = self._establish_smart_connection(server, session_name)
            if success:
                log_output("✨ 连接恢复成功!", "SUCCESS")
                return True
            else:
                log_output(f"恢复失败: {msg}", "ERROR")
                return False
                
        except Exception as e:
            log_output(f"恢复过程异常: {str(e)}", "ERROR")
            return False
    
    def _establish_smart_connection(self, server, session_name: str) -> Tuple[bool, str]:
        """建立智能连接 - 优化版本"""
        try:
            # 创建tmux会话
            create_cmd = ['tmux', 'new-session', '-d', '-s', session_name]
            result = subprocess.run(create_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return False, f"创建会话失败: {result.stderr}"
            
            # 启动连接工具
            connection_config = server.specs.get('connection', {})
            connection_tool = connection_config.get('tool', 'ssh')
            
            if connection_tool == 'relay-cli':
                success, msg = self._connect_via_relay_enhanced(server, session_name)
            else:
                success, msg = self._connect_via_ssh_enhanced(server, session_name)
            
            if not success:
                return False, msg
            
            return True, f"连接已建立"
            
        except Exception as e:
            return False, f"建立连接异常: {str(e)}"
    
    def _connect_via_relay_enhanced(self, server, session_name: str) -> Tuple[bool, str]:
        """增强版relay连接 - 支持交互引导"""
        try:
            connection_config = server.specs.get('connection', {})
            target_host = connection_config.get('target', {}).get('host', server.host)
            
            # 启动relay-cli
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'relay-cli', 'Enter'],
                         capture_output=True)
            
            # 智能等待relay就绪 - 支持交互引导
            log_output("⏳ 等待relay-cli启动...", "INFO")
            for i in range(60):  # 增加等待时间到60秒
                time.sleep(1)
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                output = result.stdout
                
                # 检查是否需要用户交互
                if i > 5:  # 5秒后开始检查交互需求
                    input_handled = self._handle_interactive_input(session_name, output)
                    if not input_handled:
                        return False, "用户输入处理失败"
                
                # 检查连接状态
                if 'succeeded' in output.lower():
                    log_output("✅ Relay认证成功", "SUCCESS")
                    break
                elif 'failed' in output.lower() and i > 30:  # 30秒后才判断失败
                    return False, "Relay认证失败"
            else:
                log_output("⚠️ Relay启动检查超时，继续尝试连接目标服务器", "WARNING")
            
            # 连接目标服务器
            time.sleep(2)
            subprocess.run(['tmux', 'send-keys', '-t', session_name, f'ssh {target_host}', 'Enter'],
                         capture_output=True)
            
            # 等待目标服务器连接 - 支持交互引导
            for i in range(30):  # 30次检查，每次2秒
                time.sleep(2)
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                output = result.stdout
                
                # 检查是否需要用户交互
                input_handled = self._handle_interactive_input(session_name, output)
                if not input_handled:
                    return False, "目标服务器连接时用户输入处理失败"
                
                # 检查连接成功
                target_short = target_host.split('.')[0]
                if target_short in output and ('@' in output or '#' in output):
                    log_output(f"✅ 已连接到目标服务器: {target_host}", "SUCCESS")
                    return True, "目标服务器连接成功"
                
                # 检查明显的错误
                if any(error in output.lower() for error in 
                       ['connection refused', 'no route to host', 'timeout']):
                    return False, f"目标服务器连接失败: {output[-200:]}"
            
            return False, "目标服务器连接超时"
            
        except Exception as e:
            return False, f"Relay连接异常: {str(e)}"
    
    def _connect_via_ssh_enhanced(self, server, session_name: str) -> Tuple[bool, str]:
        """增强版SSH连接 - 支持交互引导"""
        try:
            # 直接SSH连接
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f'ssh {server.username}@{server.host}', 'Enter'],
                         capture_output=True)
            
            # 等待连接 - 支持交互引导
            for i in range(30):  # 30次检查
                time.sleep(1)
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                output = result.stdout
                
                # 检查是否需要用户交互
                input_handled = self._handle_interactive_input(session_name, output)
                if not input_handled:
                    return False, "SSH连接时用户输入处理失败"
                
                # 检查连接成功
                if '@' in output and server.host.split('.')[0] in output:
                    log_output("✅ SSH连接成功", "SUCCESS")
                    return True, "SSH连接成功"
                
                # 检查连接错误
                if any(error in output.lower() for error in 
                       ['connection refused', 'permission denied', 'host unreachable']):
                    return False, f"SSH连接失败: {output[-200:]}"
            
            return False, "SSH连接超时"
            
        except Exception as e:
            return False, f"SSH连接异常: {str(e)}"
    
    def _setup_docker_environment(self, server, session_name: str) -> Tuple[bool, str]:
        """智能Docker环境设置"""
        try:
            docker_config = server.specs.get('docker', {})
            container_name = docker_config.get('container_name')
            
            if not container_name:
                return True, "无需Docker配置"
            
            log_output(f"🐳 设置Docker容器: {container_name}", "INFO")
            
            # 检查Docker可用性
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'docker --version', 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'command not found' in result.stdout:
                return False, "Docker未安装或不可用"
            
            # 智能容器检测
            success = self._smart_container_connect(session_name, container_name, docker_config)
            
            if success:
                log_output("🎉 Docker环境已就绪", "SUCCESS")
                return True, "Docker环境设置成功"
            else:
                return False, "Docker环境设置失败"
            
        except Exception as e:
            return False, f"Docker设置异常: {str(e)}"
    
    def _smart_container_connect(self, session_name: str, container_name: str, docker_config: dict) -> bool:
        """智能容器连接 - 自动检测和创建"""
        try:
            # 检查容器是否存在
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          f'docker inspect {container_name} >/dev/null 2>&1 && echo "EXISTS" || echo "NOT_EXISTS"', 
                          'Enter'], capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'EXISTS' in result.stdout and 'NOT_EXISTS' not in result.stdout:
                # 容器存在，检查运行状态
                log_output("✅ 容器已存在，检查状态...", "INFO")
                
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f'docker start {container_name} 2>/dev/null', 'Enter'],
                             capture_output=True)
                time.sleep(3)
                
                # 进入容器
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f'docker exec -it {container_name} bash', 'Enter'],
                             capture_output=True)
                time.sleep(2)
                
                # 验证是否成功进入
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if '@' in result.stdout or '#' in result.stdout:
                    log_output("🚀 已进入现有容器", "SUCCESS")
                    return True
                else:
                    log_output("⚠️ 进入容器失败，手动操作可能需要", "WARNING")
                    return False
            
            else:
                log_output("📦 容器不存在，将创建新容器", "INFO")
                image_name = docker_config.get('image', 'ubuntu:20.04')
                
                # 创建新容器（简化版）
                docker_cmd = f"docker run -dit --name {container_name} --privileged {image_name}"
                subprocess.run(['tmux', 'send-keys', '-t', session_name, docker_cmd, 'Enter'],
                             capture_output=True)
                
                time.sleep(10)  # 等待容器创建
                
                # 进入新容器
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              f'docker exec -it {container_name} bash', 'Enter'],
                             capture_output=True)
                time.sleep(2)
                
                log_output("🎉 新容器已创建并进入", "SUCCESS")
                return True
                
        except Exception as e:
            log_output(f"容器连接异常: {str(e)}", "ERROR")
            return False
    
    def _verify_environment(self, session_name: str) -> bool:
        """环境验证"""
        try:
            # 发送验证命令
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'pwd && whoami', 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            # 简单验证：有输出且不在本地
            if (result.returncode == 0 and 
                len(result.stdout.strip()) > 0 and 
                'MacBook-Pro' not in result.stdout):
                return True
            
            return False
            
        except Exception:
            return False
    
    def _update_progress(self, server_name: str, progress: int, message: str):
        """更新连接进度"""
        if server_name in self.connection_states:
            state = self.connection_states[server_name]
            state.progress = progress
            state.message = message
            state.last_update = time.time()
            
            # 动态进度显示
            progress_bar = "▓" * (progress // 10) + "░" * (10 - progress // 10)
            log_output(f"[{progress_bar}] {progress}% - {message}", "INFO")
    
    def _show_connection_info(self, server_name: str, session_name: str):
        """显示连接信息"""
        log_output("", "INFO")
        log_output("=" * 50, "INFO")
        log_output(f"🎉 连接成功: {server_name}", "SUCCESS")
        log_output("=" * 50, "INFO")
        log_output(f"📱 会话名称: {session_name}", "INFO")
        log_output(f"🔗 连接命令: tmux attach -t {session_name}", "INFO")
        log_output("", "INFO")
        log_output("💡 快速操作:", "INFO")
        log_output("  • 进入会话: tmux attach -t " + session_name, "INFO")
        log_output("  • 退出会话: Ctrl+B, D", "INFO")
        log_output("  • 查看状态: tmux list-sessions", "INFO")
        log_output("=" * 50, "INFO")
    
    def get_connection_status(self, server_name: str) -> Dict[str, Any]:
        """获取连接状态"""
        if server_name in self.connection_states:
            state = self.connection_states[server_name]
            return {
                "server_name": state.server_name,
                "session_name": state.session_name,
                "stage": state.stage,
                "progress": state.progress,
                "message": state.message,
                "last_update": state.last_update,
                "status": "connected" if state.progress == 100 else "connecting"
            }
        else:
            return {"error": f"No connection state found for {server_name}"}
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """列出所有服务器（继承原有功能）"""
        return self.list_servers_internal()
    
    def execute_command(self, server_name: str, command: str) -> Tuple[bool, str]:
        """执行命令（继承原有功能，但增加智能重连）"""
        try:
            # 先尝试执行
            success, output = self.execute_command_internal(server_name, command)
            
            if success:
                return True, output
            
            # 如果失败且启用自动恢复，尝试重连
            if self.auto_recovery_enabled and "会话does not exist" in output:
                log_output("🔄 检测到连接断开，尝试自动重连...", "WARNING")
                reconnect_success, msg = self.smart_connect(server_name)
                
                if reconnect_success:
                    # 重连成功，重新执行命令
                    time.sleep(2)
                    return self.execute_command_internal(server_name, command)
                else:
                    return False, f"自动重连失败: {msg}"
            
            return False, output
            
        except Exception as e:
            return False, f"命令执行异常: {str(e)}"

    def _wait_for_user_input(self, session_name: str, input_type: str, timeout: int = 300) -> bool:
        """
        等待用户输入完成
        
        Args:
            session_name: tmux会话名
            input_type: 输入类型
            timeout: 超时时间（秒）
            
        Returns:
            bool: 用户是否完成输入
        """
        guide = self.interactive_guides[session_name]
        start_time = time.time()
        check_interval = 3  # 每3秒检查一次
        
        log_output(f"⏳ 等待用户完成{input_type}输入 (超时: {timeout}秒)", "INFO")
        
        while time.time() - start_time < timeout:
            time.sleep(check_interval)
            
            try:
                # 获取当前会话输出
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if result.returncode != 0:
                    log_output("❌ 无法获取会话状态", "ERROR")
                    return False
                
                output = result.stdout
                
                # 检查是否还需要输入
                current_input_needed = guide.detect_input_needed(output)
                
                if current_input_needed != input_type:
                    # 输入需求已变化，说明用户可能已完成输入
                    log_output("✅ 检测到输入状态变化，继续连接流程", "SUCCESS")
                    return True
                
                # 检查是否有进展（新的输出）
                if len(output.strip()) > 0:
                    elapsed = time.time() - start_time
                    remaining = timeout - elapsed
                    log_output(f"🔄 仍在等待输入... (剩余 {remaining:.0f}秒)", "INFO")
                
            except Exception as e:
                log_output(f"⚠️ 检查输入状态时出错: {str(e)}", "WARNING")
                continue
        
        log_output("⏰ 等待用户输入超时", "WARNING")
        return False
    
    def _handle_interactive_input(self, session_name: str, output: str) -> bool:
        """
        处理交互式输入
        
        Args:
            session_name: tmux会话名
            output: 当前输出
            
        Returns:
            bool: 是否成功处理输入
        """
        if session_name not in self.interactive_guides:
            self.interactive_guides[session_name] = InteractiveGuide(session_name)
        
        guide = self.interactive_guides[session_name]
        input_type = guide.detect_input_needed(output)
        
        if not input_type:
            return True  # 无需输入，继续
        
        # 生成用户引导
        guide_info = guide.guide_user_input(input_type, output)
        
        # 显示引导信息
        self._show_input_guide(guide_info)
        
        # 等待用户完成输入
        if guide_info.get('auto_continue', True):
            success = self._wait_for_user_input(session_name, input_type, guide_info.get('timeout', 300))
            return success
        else:
            log_output("⚠️ 需要手动处理，请完成输入后手动继续", "WARNING")
            return False
    
    def _show_input_guide(self, guide_info: Dict[str, Any]):
        """显示用户输入引导"""
        log_output("", "INFO")
        log_output("🚨 " + "=" * 60, "WARNING")
        log_output(f"   {guide_info.get('title', '需要用户输入')}", "WARNING")
        log_output("🚨 " + "=" * 60, "WARNING")
        log_output("", "INFO")
        
        description = guide_info.get('description', '')
        if description:
            log_output(f"📋 说明: {description}", "INFO")
            log_output("", "INFO")
        
        instructions = guide_info.get('instructions', [])
        if instructions:
            log_output("📖 操作步骤:", "INFO")
            for instruction in instructions:
                log_output(f"   {instruction}", "INFO")
            log_output("", "INFO")
        
        timeout = guide_info.get('timeout', 300)
        log_output(f"⏰ 超时时间: {timeout}秒", "INFO")
        log_output("", "INFO")
        
        log_output("💡 提示: 系统将自动检测您的输入完成状态", "INFO")
        log_output("🚨 " + "=" * 60, "WARNING")
        log_output("", "INFO")


# 便捷函数
def create_enhanced_manager(config_path: Optional[str] = None) -> EnhancedSSHManager:
    """创建增强版SSH管理器"""
    return EnhancedSSHManager(config_path)


if __name__ == "__main__":
    # 测试代码
    manager = create_enhanced_manager()
    
    # 测试智能连接
    import sys
    if len(sys.argv) > 1:
        server_name = sys.argv[1]
        success, msg = manager.smart_connect(server_name)
        print(f"连接结果: {success} - {msg}")