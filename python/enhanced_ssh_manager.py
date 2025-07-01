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
        
        # 🚀 第一阶段优化：连接稳定性增强
        self.health_check_interval = 30  # 健康检查间隔(秒)
        self.max_retry_attempts = 3  # 最大重试次数
        self.connection_quality_threshold = 0.8  # 连接质量阈值
        self.heartbeat_timeout = 10  # 心跳超时时间
        self.connection_metrics: Dict[str, Dict] = {}  # 连接质量指标
        
        # 直接集成配置加载逻辑，不再依赖base_manager
        self.servers: Dict[str, Any] = {}
        self.global_settings: Dict[str, Any] = {}
        self.security_settings: Dict[str, Any] = {}
        
        # 查找并加载配置文件
        self.config_path = self._find_config_file() if config_path is None else config_path
        self._load_config()
        
        log_output("🚀 Enhanced SSH Manager 已启动", "SUCCESS")
        log_output("💡 新功能: 智能连接检测、自动Docker环境、一键恢复、交互引导", "INFO")
        log_output("🔧 连接稳定性增强: 心跳检测、自动重连、连接质量监控", "INFO")
    
    def _find_config_file(self) -> str:
        """查找配置文件"""
        # 1. 用户目录配置（修复：使用正确的目录名）
        user_config_dir = Path.home() / ".remote-terminal"
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
                
                # 保存docker配置的副本，确保server.docker始终可用
                docker_config = server_config.get('docker', {})
                
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
                    'password': server_config.get('password'),
                    'docker': docker_config  # 修复：使用保存的docker配置
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
        智能连接 - 核心用户体验优化方法 (第一阶段增强版)
        
        特性：
        1. 自动检测连接状态
        2. 智能Docker环境设置
        3. 渐进式错误恢复
        4. 实时进度反馈
        5. 🚀 连接稳定性监控 (第一阶段新增)
        6. 🚀 自动健康检查 (第一阶段新增)
        """
        server = self.get_server(server_name)
        if not server:
            return False, f"服务器 {server_name} 不存在"
        
        session_name = server.session.get('name', f"{server_name}_session") if server.session else f"{server_name}_session"
        
        # 🚀 第一阶段优化：启动连接健康监控
        self.start_connection_health_monitor(server_name)
        
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
                    # 🚀 第一阶段优化：验证连接健康状态
                    health_status = self.check_connection_health(server_name)
                    if health_status['status'] == 'healthy':
                        self._update_progress(server_name, 100, "连接已就绪且健康！")
                        log_output(f"🔍 连接质量: {health_status['connection_quality']:.2f}, 响应时间: {health_status['response_time']:.2f}s", "INFO")
                        return True, f"连接已存在且正常: {session_name}"
                    else:
                        log_output(f"⚠️ 连接存在但健康状态异常: {health_status['message']}", "WARNING")
                        # 尝试自动恢复
                        success, recovery_msg = self.auto_recovery_connection(server_name)
                        if success:
                            self._update_progress(server_name, 100, "连接已自动恢复！")
                            return True, f"连接已自动恢复: {recovery_msg}"
                elif existing_status == "recoverable":
                    log_output("🔄 检测到可恢复的连接，正在修复...", "WARNING")
                    success, recovery_msg = self.auto_recovery_connection(server_name)
                    if success:
                        self._update_progress(server_name, 100, "连接已恢复！")
                        return True, f"连接已恢复: {recovery_msg}"
            
            # 阶段2: 建立新连接
            self._update_progress(server_name, 20, "建立新连接...")
            success, msg = self._establish_smart_connection(server, session_name)
            if not success:
                self._update_progress(server_name, 0, f"连接失败: {msg}")
                return False, msg
            
            # 🚀 第一阶段优化：连接建立后立即进行健康检查
            self._update_progress(server_name, 35, "验证连接健康状态...")
            health_status = self.check_connection_health(server_name)
            if health_status['status'] != 'healthy':
                log_output(f"⚠️ 新建连接健康检查失败: {health_status['message']}", "WARNING")
                # 不立即失败，继续后续流程，可能在环境设置后恢复
            else:
                log_output(f"✅ 连接健康检查通过，质量评分: {health_status['connection_quality']:.2f}", "SUCCESS")
            
            # 阶段3: Docker环境设置
            if server.specs and server.specs.get('docker'):
                self._update_progress(server_name, 60, "设置Docker环境...")
                success, msg = self._setup_docker_environment(server, session_name)
                if not success:
                    log_output(f"Docker设置失败: {msg}", "WARNING")
                    log_output("💡 继续使用主机环境", "INFO")
            
            # 阶段3.5: 同步环境设置
            if hasattr(server, 'sync') and server.sync and server.sync.get('enabled'):
                self._update_progress(server_name, 75, "设置同步环境...")
                success, msg = self._setup_sync_environment(server, session_name)
                if not success:
                    log_output(f"同步设置失败: {msg}", "WARNING")
                    log_output("💡 继续使用普通连接", "INFO")
            
            # 阶段4: 环境验证
            self._update_progress(server_name, 90, "验证环境...")
            success = self._verify_environment(session_name)
            if not success:
                return False, "环境验证失败"
            
            # 🚀 第一阶段优化：最终健康检查和质量评估
            self._update_progress(server_name, 95, "最终健康检查...")
            final_health = self.check_connection_health(server_name)
            
            # 完成
            self._update_progress(server_name, 100, "连接已就绪！")
            
            # 显示连接信息
            self._show_connection_info(server_name, session_name)
            
            # 🚀 第一阶段优化：显示连接质量报告
            if final_health['status'] == 'healthy':
                log_output("", "INFO")
                log_output("📊 连接质量报告:", "INFO")
                log_output(f"  🎯 连接质量: {final_health['connection_quality']:.2f}/1.0", "SUCCESS")
                log_output(f"  ⚡ 响应时间: {final_health['response_time']:.2f}s", "INFO")
                log_output(f"  📈 成功率: {final_health['success_rate']:.2%}", "INFO")
                
                # 获取优化建议
                if server_name in self.connection_metrics:
                    recommendation = self._get_connection_recommendation(self.connection_metrics[server_name])
                    log_output(f"  💡 建议: {recommendation}", "INFO")
                log_output("", "INFO")
            
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
        """增强版relay连接 - 实现完整的多级跳板连接流程"""
        try:
            connection_config = server.specs.get('connection', {})
            target_host = connection_config.get('target', {}).get('host', server.host)
            username = getattr(server, 'username', 'unknown')
            
            # 检查是否为多级跳板配置
            jump_host_config = connection_config.get('jump_host')
            if jump_host_config:
                log_output(f"🔗 开始多级跳板连接流程: relay-cli -> {jump_host_config['host']} -> {target_host}", "INFO")
                return self._connect_via_multi_level_relay(server, session_name, jump_host_config, target_host, username)
            else:
                log_output(f"🔗 开始两步连接流程: relay-cli -> {target_host}", "INFO")
                return self._connect_via_simple_relay(server, session_name, target_host, username)
            
        except Exception as e:
            return False, f"Relay连接异常: {str(e)}"
    
    def _connect_via_simple_relay(self, server, session_name: str, target_host: str, username: str) -> Tuple[bool, str]:
        """通过分步send-keys实现简单relay连接"""
        try:
            log_output("📡 正在启动 relay-cli...", "INFO")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'relay-cli', 'Enter'], check=True)

            if not self._wait_for_output(session_name, ['-bash-baidu-ssl$'], timeout=60):
                return False, "连接relay-cli超时或失败"
            log_output("✅ 已连接到跳板机环境。", "SUCCESS")

            ssh_cmd = f"ssh -t {username}@{target_host}"
            log_output(f"🎯 正在通过跳板机连接到 {target_host}...", "INFO")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, ssh_cmd, 'Enter'], check=True)

            target_prompt = f"@{target_host.split('.')[0]}"
            if not self._wait_for_output(session_name, [target_prompt, f'~]$', f'# '], timeout=30):
                return False, f"登录到目标服务器 {target_host} 超时或失败"
            log_output(f"✅ 成功登录到目标: {target_host}", "SUCCESS")
            
            # --- 关键修复：调用Docker进入函数 ---
            return self._auto_enter_docker_container(server, session_name)
            
        except Exception as e:
            return False, f"简单Relay连接异常: {str(e)}"

    def _connect_via_multi_level_relay(self, server, session_name: str, jump_host_config: dict, target_host: str, username: str) -> Tuple[bool, str]:
        """通过分步send-keys实现多层relay连接"""
        try:
            # 步骤1: 连接到第一层跳板机
            jump_host_user = jump_host_config['username']
            jump_host = jump_host_config['host']
            jump_port = jump_host_config.get('port', 22)
            
            jump_cmd = f"ssh {jump_host_user}@{jump_host} -p {jump_port}"
            log_output(f"📡 正在连接到第一层跳板机: {jump_host}...", "INFO")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, jump_cmd, 'Enter'], check=True)
            
            jump_prompt = f"@{jump_host.split('.')[0]}"
            if not self._wait_for_output(session_name, [jump_prompt, f'~]$', f'# '], timeout=30):
                return False, f"登录到跳板机 {jump_host} 超时或失败"
            log_output(f"✅ 成功登录到跳板机: {jump_host}", "SUCCESS")

            # 步骤2: 从跳板机连接到最终目标
            target_cmd = f"ssh -t {username}@{target_host}"
            log_output(f"🎯 正在通过跳板机连接到最终目标: {target_host}...", "INFO")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, target_cmd, 'Enter'], check=True)

            target_prompt = f"@{target_host.split('.')[0]}"
            if not self._wait_for_output(session_name, [target_prompt, f'~]$', f'# '], timeout=30):
                return False, f"从跳板机登录到 {target_host} 超时或失败"
            log_output(f"✅ 成功登录到最终目标: {target_host}", "SUCCESS")

            # --- 关键修复：调用Docker进入函数 ---
            return self._auto_enter_docker_container(server, session_name)
            
        except Exception as e:
            return False, f"多层Relay连接异常: {str(e)}"

    def _auto_enter_docker_container(self, server, session_name: str) -> Tuple[bool, str]:
        """自动进入Docker容器 - 修复配置路径并优化检测"""
        try:
            # 修复：从正确的路径获取Docker配置
            docker_config = server.specs.get('docker', {}) if hasattr(server, 'specs') and server.specs else {}
            container_name = docker_config.get('container_name')
            shell_type = docker_config.get('shell', 'zsh')
            
            log_output(f"🔍 检查Docker配置: container_name={container_name}, shell={shell_type}", "INFO")
            
            if not container_name:
                log_output("ℹ️ 无Docker容器配置，保持主机连接", "INFO")
                return True, "无Docker容器配置，保持主机连接"
            
            log_output(f"🐳 开始进入Docker容器: {container_name}...", "INFO")
            
            # 进入Docker容器
            docker_cmd = f'docker exec -it {container_name} {shell_type}'
            log_output(f"📝 执行命令: {docker_cmd}", "INFO")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, docker_cmd, 'Enter'],
                         capture_output=True)
            
            # 优化检测：使用容器特定的快速检测命令
            log_output("⏳ 等待进入容器环境...", "INFO")
            
            # 发送快速检测命令
            time.sleep(2)  # 给docker exec一些时间
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'echo "DOCKER_CONTAINER_CHECK_$(hostname)"', 'Enter'],
                         capture_output=True)
            
            # 等待进入容器成功 - 使用更快的检测方式
            for i in range(15):  # 减少到15次检查，每次间隔更短
                time.sleep(1)
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                output = result.stdout
                log_output(f"🔍 检测第{i+1}次: {output[-100:].strip()}", "INFO")
                
                # 优化检测：首先检查是否有配置向导需要处理
                if 'Choice [ynrq]:' in output or 'Choice [ynq]:' in output or 'Powerlevel10k configuration wizard' in output:
                    log_output("⚙️ 检测到Powerlevel10k配置向导，自动跳过...", "INFO")
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, 'q', 'Enter'],
                                 capture_output=True)
                    time.sleep(2)
                    
                    # 跳过向导后，认为已经成功进入容器
                    log_output(f"✅ 成功进入Docker容器: {container_name} (跳过配置向导)", "SUCCESS")
                    
                    # 拷贝配置文件到容器
                    self._copy_zsh_configs_to_container(session_name, shell_type)
                    
                    return True, f"完整连接成功 - 容器: {container_name}"
                
                # 使用hostname检查
                if 'DOCKER_CONTAINER_CHECK_' in output:
                    log_output(f"✅ 成功进入Docker容器: {container_name}", "SUCCESS")
                    
                    # 拷贝配置文件到容器
                    self._copy_zsh_configs_to_container(session_name, shell_type)
                    
                    return True, f"完整连接成功 - 容器: {container_name}"
                
                # 检查容器错误
                if 'no such container' in output.lower() or 'not found' in output.lower():
                    log_output(f"❌ Docker容器错误: {output[-200:]}", "ERROR")
                    return False, f"Docker容器 {container_name} 不存在或未运行"
                
                # 检查其他可能的容器标志
                if any(indicator in output.lower() for indicator in ['root@', f'{shell_type}#', 'container']):
                    log_output(f"✅ 检测到容器环境标志，进入Docker容器: {container_name}", "SUCCESS")
                    
                    # 拷贝配置文件到容器
                    self._copy_zsh_configs_to_container(session_name, shell_type)
                    
                    return True, f"完整连接成功 - 容器: {container_name}"
            
            log_output("⏰ 进入Docker容器超时，但连接可能仍然有效", "WARNING")
            return False, "进入Docker容器超时"
            
        except Exception as e:
            log_output(f"💥 Docker容器连接异常: {str(e)}", "ERROR")
            return False, f"Docker容器连接异常: {str(e)}"
    
    def _copy_zsh_configs_to_container(self, session_name: str, shell_type: str) -> bool:
        """拷贝zsh配置文件到Docker容器 - 使用base64编码确保可靠传输"""
        try:
            log_output("📂 开始拷贝zsh配置文件到容器...", "INFO")
            
            # 获取templates目录路径
            script_dir = Path(__file__).parent
            project_dir = script_dir.parent
            zsh_config_dir = project_dir / "templates" / "configs" / "zsh"
            
            if not zsh_config_dir.exists():
                log_output(f"⚠️ 配置目录不存在: {zsh_config_dir}", "WARNING")
                return False
            
            # 首先确保在home目录
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'cd ~', 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            # 配置文件列表
            config_files = ['.zshrc', '.p10k.zsh']  # 暂时跳过.zsh_history，因为它可能有编码问题
            
            import base64
            
            for config_file in config_files:
                source_file = zsh_config_dir / config_file
                if source_file.exists():
                    log_output(f"📋 拷贝 {config_file} 到 ~/{config_file}...", "INFO")
                    
                    # 读取文件内容并base64编码
                    with open(source_file, 'rb') as f:
                        file_content = f.read()
                    
                    encoded_content = base64.b64encode(file_content).decode('utf-8')
                    
                    # 分块传输（避免命令行长度限制）
                    chunk_size = 1000
                    chunks = [encoded_content[i:i+chunk_size] for i in range(0, len(encoded_content), chunk_size)]
                    
                    # 清空临时文件
                    temp_file = f"{config_file}.b64"
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, f'rm -f {temp_file}', 'Enter'],
                                 capture_output=True)
                    time.sleep(0.5)
                    
                    # 逐块写入base64内容
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            cmd = f"echo '{chunk}' > {temp_file}"
                        else:
                            cmd = f"echo '{chunk}' >> {temp_file}"
                        
                        subprocess.run(['tmux', 'send-keys', '-t', session_name, cmd, 'Enter'],
                                     capture_output=True)
                        time.sleep(0.1)
                    
                    # 解码并创建最终文件
                    decode_cmd = f"base64 -d {temp_file} > {config_file} && rm {temp_file}"
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, decode_cmd, 'Enter'],
                                 capture_output=True)
                    time.sleep(1)
                    
                    # 验证文件是否创建成功
                    file_marker = config_file.replace(".", "_")
                    verify_cmd = f"ls -la {config_file} && echo 'FILE_CREATED_{file_marker}'"
                    subprocess.run(['tmux', 'send-keys', '-t', session_name, verify_cmd, 'Enter'],
                                 capture_output=True)
                    time.sleep(1)
                    
                    # 检查验证结果 - 增加重试机制
                    verification_marker = f"FILE_CREATED_{file_marker}"
                    verification_success = False
                    
                    for retry in range(3):  # 最多重试3次
                        time.sleep(0.5)  # 等待命令完成
                        result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                              capture_output=True, text=True)
                        
                        if verification_marker in result.stdout:
                            verification_success = True
                            break
                    
                    if verification_success:
                        log_output(f"✅ {config_file} 拷贝并验证成功", "SUCCESS")
                    else:
                        log_output(f"⚠️ {config_file} 验证超时，但文件可能已创建", "WARNING")
                        # 不要返回False，继续处理其他文件
                else:
                    log_output(f"⚠️ 配置文件不存在: {source_file}", "WARNING")
            
            # 设置文件权限
            log_output("🔐 设置文件权限...", "INFO")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'chmod 644 ~/.zshrc ~/.p10k.zsh', 'Enter'],
                         capture_output=True)
            time.sleep(0.5)
            
            # 禁用Powerlevel10k配置向导
            log_output("⚙️ 禁用Powerlevel10k配置向导...", "INFO")
            disable_cmd = "echo 'POWERLEVEL9K_DISABLE_CONFIGURATION_WIZARD=true' >> ~/.zshrc"
            subprocess.run(['tmux', 'send-keys', '-t', session_name, disable_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(0.5)
            
            # 重新加载zsh配置
            log_output("🔄 重新加载zsh配置...", "INFO")
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'source ~/.zshrc', 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            # 最终验证
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'echo "CONFIG_RELOAD_COMPLETE"', 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if "CONFIG_RELOAD_COMPLETE" in result.stdout:
                log_output("🎉 zsh配置文件拷贝和加载完成！", "SUCCESS")
                return True
            else:
                log_output("⚠️ 配置重新加载可能有问题", "WARNING")
                return True  # 文件拷贝成功，即使重新加载有问题
            
        except Exception as e:
            log_output(f"❌ 配置文件拷贝失败: {str(e)}", "ERROR")
            return False

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
            # 修复：从server.docker获取配置
            docker_config = server.docker
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
    
    def _setup_sync_environment(self, server, session_name: str) -> Tuple[bool, str]:
        """设置同步环境 - 部署proftpd并配置VSCode"""
        try:
            sync_config = server.sync
            remote_workspace = sync_config.get('remote_workspace', '/home/Code')
            ftp_port = sync_config.get('ftp_port', 8021)
            ftp_user = sync_config.get('ftp_user', 'ftpuser')
            ftp_password = sync_config.get('ftp_password', 'your_ftp_password')
            
            log_output(f"🔄 开始设置同步环境...", "INFO")
            log_output(f"   远程工作目录: {remote_workspace}", "INFO")
            log_output(f"   FTP端口: {ftp_port}", "INFO")
            
            # 步骤1: 创建远程工作目录
            success = self._create_remote_workspace(session_name, remote_workspace)
            if not success:
                return False, "创建远程工作目录失败"
            
            # 步骤2: 部署proftpd
            success = self._deploy_proftpd(session_name, remote_workspace)
            if not success:
                return False, "部署proftpd失败"
            
            # 步骤3: 配置并启动proftpd
            success = self._configure_and_start_proftpd(session_name, remote_workspace, ftp_port, ftp_user, ftp_password)
            if not success:
                return False, "配置proftpd失败"
            
            # 步骤4: 配置本地VSCode
            success = self._configure_vscode_sync(server.name, sync_config)
            if not success:
                log_output("⚠️ VSCode配置失败，但同步服务器已启动", "WARNING")
                log_output("💡 请手动配置VSCode SFTP插件", "INFO")
            
            log_output("✅ 同步环境设置完成", "SUCCESS")
            return True, "同步环境设置成功"
            
        except Exception as e:
            return False, f"同步环境设置异常: {str(e)}"
    
    def _create_remote_workspace(self, session_name: str, remote_workspace: str) -> bool:
        """创建远程工作目录"""
        try:
            log_output(f"📁 创建远程工作目录: {remote_workspace}", "INFO")
            
            # 创建目录命令
            create_cmd = f"mkdir -p {remote_workspace}"
            subprocess.run(['tmux', 'send-keys', '-t', session_name, create_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            # 验证目录创建
            check_cmd = f"ls -la {remote_workspace} && echo 'WORKSPACE_CREATED'"
            subprocess.run(['tmux', 'send-keys', '-t', session_name, check_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'WORKSPACE_CREATED' in result.stdout:
                log_output("✅ 远程工作目录创建成功", "SUCCESS")
                return True
            else:
                log_output("❌ 远程工作目录创建失败", "ERROR")
                return False
                
        except Exception as e:
            log_output(f"创建远程工作目录异常: {str(e)}", "ERROR")
            return False
    
    def _deploy_proftpd(self, session_name: str, remote_workspace: str) -> bool:
        """部署proftpd到远程服务器"""
        try:
            log_output("📦 部署proftpd到远程服务器...", "INFO")
            
            # 获取proftpd.tar.gz的路径
            from pathlib import Path
            proftpd_source = Path.home() / ".remote-terminal" / "templates" / "proftpd.tar.gz"
            
            if not proftpd_source.exists():
                log_output(f"❌ 未找到proftpd.tar.gz: {proftpd_source}", "ERROR")
                return False
            
            # 使用scp上传proftpd.tar.gz到远程工作目录
            # 这里需要获取当前连接的主机信息
            upload_cmd = f"cd {remote_workspace}"
            subprocess.run(['tmux', 'send-keys', '-t', session_name, upload_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            # 由于我们已经在远程会话中，我们需要通过其他方式传输文件
            # 这里使用base64编码的方式传输小文件
            log_output("📤 使用base64编码传输proftpd.tar.gz...", "INFO")
            
            # 读取proftpd.tar.gz并base64编码
            import base64
            with open(proftpd_source, 'rb') as f:
                file_content = f.read()
            
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            
            # 分块传输（避免命令行长度限制）
            chunk_size = 1000
            chunks = [encoded_content[i:i+chunk_size] for i in range(0, len(encoded_content), chunk_size)]
            
            # 清空目标文件
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 'rm -f proftpd.tar.gz.b64', 'Enter'],
                         capture_output=True)
            time.sleep(1)
            
            # 逐块写入
            for i, chunk in enumerate(chunks):
                if i == 0:
                    cmd = f"echo '{chunk}' > proftpd.tar.gz.b64"
                else:
                    cmd = f"echo '{chunk}' >> proftpd.tar.gz.b64"
                
                subprocess.run(['tmux', 'send-keys', '-t', session_name, cmd, 'Enter'],
                             capture_output=True)
                time.sleep(0.1)
            
            # 解码文件
            decode_cmd = "base64 -d proftpd.tar.gz.b64 > proftpd.tar.gz && rm proftpd.tar.gz.b64"
            subprocess.run(['tmux', 'send-keys', '-t', session_name, decode_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            # 验证文件传输
            check_cmd = "ls -la proftpd.tar.gz && echo 'PROFTPD_UPLOADED'"
            subprocess.run(['tmux', 'send-keys', '-t', session_name, check_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'PROFTPD_UPLOADED' in result.stdout:
                log_output("✅ proftpd.tar.gz上传成功", "SUCCESS")
                
                # 解压文件
                extract_cmd = "tar -xzf proftpd.tar.gz && echo 'PROFTPD_EXTRACTED'"
                subprocess.run(['tmux', 'send-keys', '-t', session_name, extract_cmd, 'Enter'],
                             capture_output=True)
                time.sleep(3)
                
                result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                      capture_output=True, text=True)
                
                if 'PROFTPD_EXTRACTED' in result.stdout:
                    log_output("✅ proftpd解压成功", "SUCCESS")
                    return True
                else:
                    log_output("❌ proftpd解压失败", "ERROR")
                    return False
            else:
                log_output("❌ proftpd.tar.gz上传失败", "ERROR")
                return False
                
        except Exception as e:
            log_output(f"部署proftpd异常: {str(e)}", "ERROR")
            return False
    
    def _configure_and_start_proftpd(self, session_name: str, remote_workspace: str, ftp_port: int, ftp_user: str, ftp_password: str) -> bool:
        """配置并启动proftpd服务"""
        try:
            log_output("⚙️ 配置并启动proftpd服务...", "INFO")
            
            # 执行初始化脚本
            init_cmd = f"bash ./init.sh {remote_workspace}"
            subprocess.run(['tmux', 'send-keys', '-t', session_name, init_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(5)
            
            # 检查初始化结果
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            log_output("📋 初始化脚本输出:", "INFO")
            log_output(result.stdout[-500:], "DEBUG")  # 显示最后500字符
            
            # 启动proftpd服务
            start_cmd = f"./proftpd -n -c ./proftpd.conf &"
            subprocess.run(['tmux', 'send-keys', '-t', session_name, start_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(3)
            
            # 验证服务启动
            check_cmd = f"netstat -tlnp | grep {ftp_port} && echo 'PROFTPD_RUNNING'"
            subprocess.run(['tmux', 'send-keys', '-t', session_name, check_cmd, 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            if 'PROFTPD_RUNNING' in result.stdout or str(ftp_port) in result.stdout:
                log_output(f"✅ proftpd服务已启动，监听端口: {ftp_port}", "SUCCESS")
                log_output(f"   FTP用户: {ftp_user}", "INFO")
                log_output(f"   工作目录: {remote_workspace}", "INFO")
                return True
            else:
                log_output("❌ proftpd服务启动失败", "ERROR")
                return False
                
        except Exception as e:
            log_output(f"配置proftpd异常: {str(e)}", "ERROR")
            return False
    
    def _configure_vscode_sync(self, server_name: str, sync_config: dict) -> bool:
        """配置VSCode同步"""
        try:
            log_output("🔧 配置VSCode同步...", "INFO")
            
            # 导入VSCode同步管理器
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            
            from vscode_sync_manager import create_vscode_sync_manager
            
            # 创建同步管理器
            local_workspace = sync_config.get('local_workspace', os.getcwd())
            sync_manager = create_vscode_sync_manager(local_workspace)
            
            # 验证工作目录
            if not sync_manager.validate_workspace():
                log_output("⚠️ 当前目录可能不是项目根目录", "WARNING")
            
            # 准备同步配置
            vscode_sync_config = {
                'host': 'localhost',  # 通过SSH隧道连接
                'ftp_port': sync_config.get('ftp_port', 8021),
                'ftp_user': sync_config.get('ftp_user', 'ftpuser'),
                'ftp_password': sync_config.get('ftp_password'),
                'remote_workspace': sync_config.get('remote_workspace', '/home/Code')
            }
            
            # 添加或更新profile
            success = sync_manager.add_or_update_profile(server_name, vscode_sync_config)
            if not success:
                return False
            
            # 尝试设置为活动profile
            profile_name = f"remote-terminal-{server_name}"
            sync_manager.set_active_profile(profile_name)
            
            log_output("✅ VSCode同步配置完成", "SUCCESS")
            log_output(f"💡 请在VSCode中使用SFTP插件连接到profile: {profile_name}", "INFO")
            
            return True
            
        except Exception as e:
            log_output(f"配置VSCode同步异常: {str(e)}", "ERROR")
            return False
    
    def _smart_container_connect(self, session_name: str, container_name: str, docker_config: dict) -> bool:
        """智能容器连接 - 自动检测和创建，配置本地环境"""
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
                    # 设置本地配置环境
                    self._setup_local_config_environment(session_name, docker_config)
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
                # 设置本地配置环境
                self._setup_local_config_environment(session_name, docker_config)
                return True
                
        except Exception as e:
            log_output(f"容器连接异常: {str(e)}", "ERROR")
            return False
    
    def _setup_local_config_environment(self, session_name: str, docker_config: dict) -> bool:
        """设置本地配置环境 - 只有zsh时才复制配置"""
        try:
            log_output("🔧 开始设置本地配置环境...", "INFO")
            
            # 获取shell类型
            shell_type = docker_config.get('shell', 'bash')
            log_output(f"📋 配置Shell类型: {shell_type}", "INFO")
            
            # 只有选择zsh时才进行配置复制
            if shell_type == 'zsh':
                log_output("🐚 检测到zsh，开始配置复制...", "INFO")
                
                # 检测配置文件来源
                config_source = self._detect_config_source(shell_type)
                if not config_source:
                    log_output("⚠️ 未找到zsh配置文件，使用默认配置", "WARNING")
                    return self._setup_default_config(session_name, shell_type)
                
                log_output(f"📁 配置来源: {config_source['type']} - {config_source['path']}", "INFO")
                
                # 复制配置文件到容器
                success = self._copy_config_files_to_container(session_name, config_source, shell_type)
                if not success:
                    log_output("❌ zsh配置文件复制失败，使用默认配置", "ERROR")
                    return self._setup_default_config(session_name, shell_type)
                
                # 应用zsh配置
                self._apply_shell_config(session_name, shell_type)
                log_output("✅ zsh配置环境设置完成", "SUCCESS")
                
            else:
                # bash使用系统默认配置，不进行复制
                log_output("🐚 检测到bash，使用系统默认配置", "INFO")
                self._setup_default_config(session_name, shell_type)
                log_output("✅ bash环境设置完成（使用系统默认）", "SUCCESS")
            
            return True
            
        except Exception as e:
            log_output(f"本地配置环境设置异常: {str(e)}", "ERROR")
            return False
    
    def _detect_config_source(self, shell_type: str) -> dict:
        """检测配置文件来源"""
        from pathlib import Path
        
        # 优先级1: 用户配置目录
        user_config_dir = Path.home() / ".remote-terminal" / "configs" / shell_type
        if user_config_dir.exists() and any(user_config_dir.glob(".*")):
            log_output(f"📁 找到用户配置目录: {user_config_dir}", "INFO")
            return {
                "type": "用户配置",
                "path": str(user_config_dir),
                "priority": 1
            }
        
        # 优先级2: 项目模板目录
        project_template_dir = Path(__file__).parent.parent / "templates" / "configs" / shell_type
        if project_template_dir.exists() and any(project_template_dir.glob(".*")):
            log_output(f"📁 找到项目模板目录: {project_template_dir}", "INFO")
            return {
                "type": "项目模板",
                "path": str(project_template_dir),
                "priority": 2
            }
        
        log_output(f"⚠️ 未找到{shell_type}配置文件目录", "WARNING")
        return None
    
    def _copy_config_files_to_container(self, session_name: str, config_source: dict, shell_type: str) -> bool:
        """复制zsh配置文件到容器"""
        try:
            source_path = config_source['path']
            log_output(f"📋 复制{shell_type}配置文件从: {source_path}", "INFO")
            
            # 简化方案：直接在容器内创建配置文件内容
            # 这样避免了复杂的容器名称获取和docker cp操作
            import os
            
            copied_files = 0
            # 读取配置文件内容并在容器内创建
            for config_file in os.listdir(source_path):
                if config_file.startswith('.'):  # 只处理隐藏配置文件
                    source_file = os.path.join(source_path, config_file)
                    if os.path.isfile(source_file):
                        try:
                            # 读取配置文件内容，处理编码问题
                            try:
                                with open(source_file, 'r', encoding='utf-8') as f:
                                    content = f.read()
                            except UnicodeDecodeError:
                                # 如果是二进制文件（如.zsh_history），跳过
                                log_output(f"⚠️ 跳过二进制文件: {config_file}", "WARNING")
                                continue
                            
                            # 在容器内创建配置文件
                            # 使用cat命令创建文件，避免特殊字符问题
                            log_output(f"📝 创建配置文件: {config_file}", "INFO")
                            
                            # 创建文件的命令
                            create_cmd = f"cat > ~/{config_file} << 'EOF_CONFIG_FILE'\n{content}\nEOF_CONFIG_FILE"
                            
                            # 发送命令到容器
                            subprocess.run(['tmux', 'send-keys', '-t', session_name, create_cmd, 'Enter'],
                                         capture_output=True)
                            time.sleep(1)
                            
                            log_output(f"✅ 已创建: {config_file}", "INFO")
                            copied_files += 1
                            
                        except Exception as e:
                            log_output(f"⚠️ 处理配置文件失败: {config_file} - {str(e)}", "WARNING")
            
            if copied_files > 0:
                log_output(f"✅ 成功复制 {copied_files} 个配置文件", "SUCCESS")
                return True
            else:
                log_output(f"⚠️ 未找到可复制的配置文件", "WARNING")
                return False
            
        except Exception as e:
            log_output(f"配置文件复制异常: {str(e)}", "ERROR")
            return False
    
    def _get_current_container_name(self, session_name: str) -> str:
        """获取当前容器名称"""
        try:
            # 在容器内执行hostname命令获取容器ID
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          'echo "CONTAINER_ID_START"; hostname; echo "CONTAINER_ID_END"', 'Enter'],
                         capture_output=True)
            time.sleep(2)
            
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True)
            
            # 解析容器ID
            lines = result.stdout.split('\n')
            container_id = None
            capture = False
            for line in lines:
                if 'CONTAINER_ID_START' in line:
                    capture = True
                    continue
                elif 'CONTAINER_ID_END' in line:
                    break
                elif capture and line.strip():
                    container_id = line.strip()
                    break
            
            if container_id:
                # 通过容器ID获取容器名称
                result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}', '--filter', f'id={container_id}'],
                                      capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            
            return None
            
        except Exception as e:
            log_output(f"获取容器名称异常: {str(e)}", "ERROR")
            return None
    
    def _apply_shell_config(self, session_name: str, shell_type: str):
        """应用Shell配置"""
        try:
            log_output(f"🔄 应用{shell_type}配置...", "INFO")
            
            if shell_type == 'zsh':
                # 启动zsh并应用配置
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 'zsh', 'Enter'],
                             capture_output=True)
                time.sleep(2)
                
                # 重新加载zsh配置
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 'source ~/.zshrc', 'Enter'],
                             capture_output=True)
                time.sleep(1)
                
            elif shell_type == 'bash':
                # 重新加载bash配置
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 'source ~/.bashrc', 'Enter'],
                             capture_output=True)
                time.sleep(1)
            
            log_output(f"✅ {shell_type}配置已应用", "SUCCESS")
            
        except Exception as e:
            log_output(f"应用Shell配置异常: {str(e)}", "ERROR")
    
    def _setup_default_config(self, session_name: str, shell_type: str) -> bool:
        """设置默认配置"""
        try:
            log_output("🔧 设置默认配置...", "INFO")
            
            # 设置基本环境变量
            subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                          'export TERM=xterm-256color', 'Enter'],
                         capture_output=True)
            time.sleep(0.5)
            
            if shell_type == 'zsh':
                # 基本zsh配置
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              'echo "export TERM=xterm-256color" >> ~/.zshrc', 'Enter'],
                             capture_output=True)
                time.sleep(0.5)
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 'zsh', 'Enter'],
                             capture_output=True)
            else:
                # 基本bash配置
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 
                              'echo "export TERM=xterm-256color" >> ~/.bashrc', 'Enter'],
                             capture_output=True)
                time.sleep(0.5)
                subprocess.run(['tmux', 'send-keys', '-t', session_name, 'source ~/.bashrc', 'Enter'],
                             capture_output=True)
            
            log_output("✅ 默认配置设置完成", "SUCCESS")
            return True
            
        except Exception as e:
            log_output(f"默认配置设置异常: {str(e)}", "ERROR")
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
        """获取连接状态 - 第一阶段增强版"""
        try:
            # 基础连接状态
            base_status = {}
            if server_name in self.connection_states:
                state = self.connection_states[server_name]
                base_status = {
                    "server_name": state.server_name,
                    "session_name": state.session_name,
                    "stage": state.stage,
                    "progress": state.progress,
                    "message": state.message,
                    "last_update": state.last_update,
                    "status": "connected" if state.progress == 100 else "connecting"
                }
            else:
                base_status = {
                    "server_name": server_name,
                    "status": "disconnected",
                    "message": "未建立连接"
                }
            
            # 🚀 第一阶段增强：添加健康监控数据
            health_data = {}
            if server_name in self.connection_metrics:
                try:
                    health_check = self.check_connection_health(server_name)
                    metrics = self.connection_metrics[server_name]
                    
                    health_data = {
                        "health_status": health_check.get('status', 'unknown'),
                        "connection_quality": health_check.get('connection_quality', 0),
                        "response_time": health_check.get('response_time', 0),
                        "avg_response_time": health_check.get('avg_response_time', 0),
                        "success_rate": health_check.get('success_rate', 0),
                        "total_checks": metrics.get('total_checks', 0),
                        "failed_checks": metrics.get('failed_checks', 0),
                        "auto_recovery_count": metrics.get('auto_recovery_count', 0),
                        "last_heartbeat": metrics.get('last_heartbeat', 0),
                        "recommendation": self._get_connection_recommendation(metrics)
                    }
                except Exception as e:
                    health_data = {"health_error": f"健康检查失败: {str(e)}"}
            
            # 🚀 第一阶段增强：添加会话信息
            session_info = {}
            if base_status.get("session_name"):
                session_name = base_status["session_name"]
                try:
                    # 检查tmux会话是否存在
                    session_check = subprocess.run(['tmux', 'has-session', '-t', session_name], 
                                                 capture_output=True)
                    session_info["tmux_session_exists"] = session_check.returncode == 0
                    
                    if session_info["tmux_session_exists"]:
                        # 获取会话详细信息
                        session_list = subprocess.run(['tmux', 'list-sessions', '-F', '#{session_name}:#{session_created}:#{session_last_attached}'], 
                                                    capture_output=True, text=True)
                        if session_check.returncode == 0:
                            for line in session_list.stdout.strip().split('\\n'):
                                if line.startswith(session_name + ':'):
                                    parts = line.split(':')
                                    if len(parts) >= 3:
                                        session_info["created_time"] = parts[1]
                                        session_info["last_attached"] = parts[2]
                                    break
                except Exception as e:
                    session_info["session_error"] = f"获取会话信息失败: {str(e)}"
            
            # 🚀 第一阶段增强：添加服务器配置信息
            server_config = {}
            server = self.get_server(server_name)
            if server:
                server_config = {
                    "host": getattr(server, 'host', 'unknown'),
                    "port": getattr(server, 'port', 22),
                    "user": getattr(server, 'user', 'unknown'),
                    "connection_type": getattr(server, 'type', 'ssh'),
                    "description": getattr(server, 'description', ''),
                    "has_docker": bool(getattr(server, 'specs', {}).get('docker')),
                    "has_sync": bool(getattr(server, 'sync', {}).get('enabled'))
                }
            
            # 合并所有状态信息
            complete_status = {
                **base_status,
                "health": health_data,
                "session": session_info,
                "server_config": server_config,
                "timestamp": time.time()
            }
            
            return complete_status
            
        except Exception as e:
            return {
                "error": f"获取连接状态失败: {str(e)}",
                "server_name": server_name,
                "status": "error"
            }
    
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
    
    def disconnect_server(self, server_name: str, force: bool = False) -> Dict[str, Any]:
        """
        断开与指定服务器的连接并清理资源
        
        Args:
            server_name: 服务器名称
            force: 是否强制断开（即使有活动会话）
            
        Returns:
            Dict: 包含断开连接结果的字典
        """
        try:
            log_output(f"🔌 开始断开服务器连接: {server_name}", "INFO")
            
            # 获取服务器配置
            server = self.get_server(server_name)
            if not server:
                return {
                    "success": False,
                    "error": f"Server '{server_name}' not found",
                    "suggestions": ["Check server name spelling", "Use list_servers to see available servers"]
                }
            
            cleanup_actions = []
            warnings = []
            
            # 1. 检查当前连接状态
            status = self.get_connection_status(server_name)
            if not status.get('connected', False):
                log_output(f"ℹ️ 服务器 '{server_name}' 已经处于断开状态", "INFO")
                return {
                    "success": True,
                    "message": f"Server '{server_name}' is already disconnected",
                    "status": "already_disconnected"
                }
            
            # 2. 获取会话信息
            session_name = server.get('session', {}).get('name', f"{server_name}_session")
            
            # 3. 检查活动会话
            try:
                result = subprocess.run(['tmux', 'list-sessions'], 
                                      capture_output=True, text=True, timeout=10)
                sessions_output = result.stdout
                
                active_sessions = []
                if session_name in sessions_output:
                    # 检查会话中的窗口和连接
                    try:
                        windows_result = subprocess.run(['tmux', 'list-windows', '-t', session_name],
                                                      capture_output=True, text=True, timeout=10)
                        if windows_result.returncode == 0:
                            windows_count = len(windows_result.stdout.strip().split('\n'))
                            active_sessions.append({
                                'name': session_name,
                                'windows': windows_count
                            })
                    except subprocess.TimeoutExpired:
                        warnings.append("Timeout checking session windows")
                        
            except subprocess.TimeoutExpired:
                warnings.append("Timeout checking tmux sessions")
                active_sessions = []
            except Exception as e:
                warnings.append(f"Error checking sessions: {str(e)}")
                active_sessions = []
            
            # 4. 处理活动会话
            if active_sessions and not force:
                return {
                    "success": False,
                    "error": f"Active sessions found for '{server_name}'",
                    "active_sessions": active_sessions,
                    "suggestions": [
                        "Use force=True to forcefully disconnect",
                        "Manually close sessions first: tmux kill-session -t " + session_name,
                        "Check for running processes in the session"
                    ]
                }
            
            # 5. 强制断开或清理会话
            if active_sessions:
                log_output(f"⚠️ 强制断开模式：清理活动会话", "WARNING")
                try:
                    # 杀死tmux会话
                    subprocess.run(['tmux', 'kill-session', '-t', session_name], 
                                 capture_output=True, timeout=15)
                    cleanup_actions.append(f"Killed tmux session: {session_name}")
                    log_output(f"🗑️ 已清理tmux会话: {session_name}", "SUCCESS")
                except subprocess.TimeoutExpired:
                    warnings.append("Timeout killing tmux session")
                except Exception as e:
                    warnings.append(f"Error killing session: {str(e)}")
            
            # 6. 清理连接状态和监控
            if server_name in self.connection_states:
                del self.connection_states[server_name]
                cleanup_actions.append("Cleared connection state")
            
            if server_name in self.connection_metrics:
                del self.connection_metrics[server_name]
                cleanup_actions.append("Cleared connection metrics")
            
            if server_name in self.interactive_guides:
                del self.interactive_guides[server_name]
                cleanup_actions.append("Cleared interactive guides")
            
            # 7. 清理SSH连接（如果有持久连接）
            try:
                # 检查并清理SSH控制套接字
                ssh_control_path = f"/tmp/ssh-{server_name}-control"
                if os.path.exists(ssh_control_path):
                    os.remove(ssh_control_path)
                    cleanup_actions.append("Removed SSH control socket")
            except Exception as e:
                warnings.append(f"Error cleaning SSH control socket: {str(e)}")
            
            # 8. 更新服务器连接状态
            if hasattr(server, 'session'):
                server.session = {}
            
            log_output(f"✅ 服务器 '{server_name}' 断开连接完成", "SUCCESS")
            
            result = {
                "success": True,
                "message": f"Successfully disconnected from '{server_name}'",
                "cleanup_actions": cleanup_actions,
                "server_name": server_name
            }
            
            if warnings:
                result["warnings"] = warnings
                
            if force and active_sessions:
                result["force_disconnect"] = True
                result["cleaned_sessions"] = [s['name'] for s in active_sessions]
            
            return result
            
        except Exception as e:
            log_output(f"❌ 断开连接时发生错误: {str(e)}", "ERROR")
            return {
                "success": False,
                "error": f"Exception during disconnect: {str(e)}",
                "server_name": server_name,
                "suggestions": [
                    "Check if tmux is properly installed",
                    "Verify server configuration",
                    "Try manual cleanup: tmux kill-session -t " + server_name + "_session"
                ]
            }

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

    # 🚀 第一阶段优化：连接健康检查系统
    def start_connection_health_monitor(self, server_name: str) -> bool:
        """启动连接健康监控"""
        try:
            if server_name not in self.connection_metrics:
                self.connection_metrics[server_name] = {
                    'last_heartbeat': time.time(),
                    'response_times': [],
                    'success_rate': 1.0,
                    'total_checks': 0,
                    'failed_checks': 0,
                    'connection_quality': 1.0,
                    'auto_recovery_count': 0
                }
            
            log_output(f"🔍 启动连接健康监控: {server_name}", "INFO")
            return True
            
        except Exception as e:
            log_output(f"健康监控启动失败: {str(e)}", "ERROR")
            return False
    
    def check_connection_health(self, server_name: str) -> Dict[str, Any]:
        """检查连接健康状态"""
        try:
            server = self.get_server(server_name)
            if not server:
                return {"status": "error", "message": "服务器不存在"}
            
            session_name = server.session.get('name', f"{server_name}_session") if server.session else f"{server_name}_session"
            
            # 初始化指标
            if server_name not in self.connection_metrics:
                self.start_connection_health_monitor(server_name)
            
            metrics = self.connection_metrics[server_name]
            start_time = time.time()
            
            # 发送心跳检测命令
            heartbeat_cmd = f'echo "HEARTBEAT_$(date +%s)_RESPONSE"'
            subprocess.run(['tmux', 'send-keys', '-t', session_name, heartbeat_cmd, 'Enter'], 
                         capture_output=True, timeout=5)
            
            # 等待响应
            time.sleep(2)
            result = subprocess.run(['tmux', 'capture-pane', '-t', session_name, '-p'],
                                  capture_output=True, text=True, timeout=5)
            
            response_time = time.time() - start_time
            metrics['total_checks'] += 1
            
            if result.returncode == 0 and 'HEARTBEAT_' in result.stdout and 'RESPONSE' in result.stdout:
                # 连接正常
                metrics['last_heartbeat'] = time.time()
                metrics['response_times'].append(response_time)
                
                # 保持最近20次响应时间
                if len(metrics['response_times']) > 20:
                    metrics['response_times'] = metrics['response_times'][-20:]
                
                # 计算连接质量
                avg_response_time = sum(metrics['response_times']) / len(metrics['response_times'])
                metrics['success_rate'] = (metrics['total_checks'] - metrics['failed_checks']) / metrics['total_checks']
                
                # 连接质量评分 (响应时间和成功率的综合评分)
                time_score = max(0, 1 - (avg_response_time - 1) / 10)  # 1秒以内满分，超过逐渐降分
                quality_score = (metrics['success_rate'] * 0.7) + (time_score * 0.3)
                metrics['connection_quality'] = max(0, min(1, quality_score))
                
                return {
                    "status": "healthy",
                    "response_time": response_time,
                    "avg_response_time": avg_response_time,
                    "success_rate": metrics['success_rate'],
                    "connection_quality": metrics['connection_quality'],
                    "message": "连接健康"
                }
            else:
                # 连接异常
                metrics['failed_checks'] += 1
                metrics['success_rate'] = (metrics['total_checks'] - metrics['failed_checks']) / metrics['total_checks']
                
                return {
                    "status": "unhealthy",
                    "response_time": response_time,
                    "success_rate": metrics['success_rate'],
                    "connection_quality": 0,
                    "message": "连接无响应或异常"
                }
                
        except subprocess.TimeoutExpired:
            metrics['failed_checks'] += 1
            return {
                "status": "timeout", 
                "message": "心跳检测超时",
                "connection_quality": 0
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"健康检查异常: {str(e)}",
                "connection_quality": 0
            }
    
    def auto_recovery_connection(self, server_name: str) -> Tuple[bool, str]:
        """自动恢复连接"""
        try:
            log_output(f"🔄 开始自动恢复连接: {server_name}", "WARNING")
            
            if server_name not in self.connection_metrics:
                self.start_connection_health_monitor(server_name)
            
            metrics = self.connection_metrics[server_name]
            metrics['auto_recovery_count'] += 1
            
            # 检查是否超过最大重试次数
            if metrics['auto_recovery_count'] > self.max_retry_attempts:
                return False, f"超过最大重试次数({self.max_retry_attempts})，请手动检查"
            
            # 尝试智能恢复
            success = self._recover_connection(server_name, 
                                             f"{server_name}_session")
            
            if success:
                metrics['auto_recovery_count'] = 0  # 重置重试计数
                log_output(f"✅ 自动恢复成功: {server_name}", "SUCCESS")
                return True, "自动恢复成功"
            else:
                return False, f"自动恢复失败 (尝试次数: {metrics['auto_recovery_count']})"
                
        except Exception as e:
            return False, f"自动恢复异常: {str(e)}"
    
    def get_connection_quality_report(self, server_name: str = None) -> Dict[str, Any]:
        """获取连接质量报告"""
        try:
            if server_name:
                # 单个服务器报告
                if server_name not in self.connection_metrics:
                    return {"error": f"没有找到服务器 {server_name} 的监控数据"}
                
                metrics = self.connection_metrics[server_name]
                health_status = self.check_connection_health(server_name)
                
                return {
                    "server_name": server_name,
                    "connection_quality": metrics.get('connection_quality', 0),
                    "success_rate": metrics.get('success_rate', 0),
                    "total_checks": metrics.get('total_checks', 0),
                    "failed_checks": metrics.get('failed_checks', 0),
                    "auto_recovery_count": metrics.get('auto_recovery_count', 0),
                    "avg_response_time": sum(metrics.get('response_times', [1])) / len(metrics.get('response_times', [1])),
                    "last_heartbeat": metrics.get('last_heartbeat', 0),
                    "current_status": health_status.get('status', 'unknown'),
                    "recommendation": self._get_connection_recommendation(metrics)
                }
            else:
                # 所有服务器总览
                report = {
                    "total_servers": len(self.connection_metrics),
                    "healthy_servers": 0,
                    "unhealthy_servers": 0,
                    "servers": {}
                }
                
                for srv_name in self.connection_metrics:
                    server_report = self.get_connection_quality_report(srv_name)
                    if server_report.get('connection_quality', 0) >= self.connection_quality_threshold:
                        report['healthy_servers'] += 1
                    else:
                        report['unhealthy_servers'] += 1
                    
                    report['servers'][srv_name] = server_report
                
                return report
                
        except Exception as e:
            return {"error": f"生成质量报告失败: {str(e)}"}
    
    def _get_connection_recommendation(self, metrics: Dict) -> str:
        """获取连接优化建议"""
        quality = metrics.get('connection_quality', 0)
        success_rate = metrics.get('success_rate', 0)
        avg_response_time = sum(metrics.get('response_times', [1])) / len(metrics.get('response_times', [1]))
        
        if quality >= 0.9:
            return "连接状态优秀，无需优化"
        elif quality >= 0.7:
            if avg_response_time > 3:
                return "连接稳定但响应较慢，建议检查网络延迟"
            else:
                return "连接状态良好"
        elif quality >= 0.5:
            if success_rate < 0.8:
                return "连接不稳定，建议检查网络环境或服务器状态"
            else:
                return "连接质量一般，建议监控并考虑优化"
        else:
            return "连接质量差，建议立即检查并修复连接问题"

    # 🚀 第一阶段优化：连接状态监控仪表板
    def show_connection_dashboard(self, server_name: str = None) -> None:
        """显示连接状态仪表板"""
        try:
            log_output("", "INFO")
            log_output("🔍 " + "=" * 60, "INFO")
            log_output("   连接状态监控仪表板", "INFO")
            log_output("🔍 " + "=" * 60, "INFO")
            log_output("", "INFO")
            
            if server_name:
                # 显示单个服务器详细状态
                self._show_single_server_dashboard(server_name)
            else:
                # 显示所有服务器概览
                self._show_all_servers_dashboard()
                
        except Exception as e:
            log_output(f"❌ 显示仪表板失败: {str(e)}", "ERROR")
    
    def _show_single_server_dashboard(self, server_name: str) -> None:
        """显示单个服务器的详细仪表板"""
        try:
            # 获取连接状态
            status = self.get_connection_status(server_name)
            
            if "error" in status:
                log_output(f"❌ 无法获取服务器 {server_name} 的状态: {status.get('error', '未知错误')}", "ERROR")
                return
            
            # 显示服务器基本信息
            log_output(f"🖥️  服务器: {server_name}", "INFO")
            log_output(f"📍 地址: {status.get('host', 'unknown')}:{status.get('port', 22)}", "INFO")
            log_output(f"👤 用户: {status.get('user', 'unknown')}", "INFO")
            log_output("", "INFO")
            
            # 显示连接状态
            connection_status = status.get("status", "unknown")
            status_icon = "✅" if connection_status == "connected" else "❌" if connection_status == "disconnected" else "⚠️"
            log_output(f"{status_icon} 连接状态: {connection_status}", "INFO")
            
            # 显示会话信息
            session_info = status.get("session", {})
            if session_info.get("session_name"):
                session_exists = "✅" if session_info.get("tmux_session_exists", False) else "❌"
                log_output(f"🖥️  会话: {session_info.get('session_name')} {session_exists}", "INFO")
                
                if session_info.get("created_time"):
                    log_output(f"⏰ 创建时间: {session_info.get('created_time')}", "INFO")
                if session_info.get("last_attached"):
                    log_output(f"🔗 最后连接: {session_info.get('last_attached')}", "INFO")
            
            log_output("", "INFO")
            
            # 显示健康监控数据
            health_data = status.get("health", {})
            if health_data:
                quality = health_data.get("connection_quality", 0)
                quality_icon = "🟢" if quality >= 0.8 else "🟡" if quality >= 0.5 else "🔴"
                log_output(f"{quality_icon} 连接质量: {quality:.2f}", "INFO")
                
                success_rate = health_data.get("success_rate", 0)
                success_icon = "✅" if success_rate >= 0.9 else "⚠️" if success_rate >= 0.7 else "❌"
                log_output(f"{success_icon} 成功率: {success_rate:.1%}", "INFO")
                
                if health_data.get("avg_response_time"):
                    response_time = health_data.get("avg_response_time")
                    time_icon = "⚡" if response_time < 1 else "🐌" if response_time > 3 else "⏱️"
                    log_output(f"{time_icon} 平均响应: {response_time:.2f}秒", "INFO")
                
                if health_data.get("auto_recovery_count", 0) > 0:
                    log_output(f"🔄 自动恢复: {health_data.get('auto_recovery_count')}次", "WARNING")
                
                # 显示建议
                recommendation = health_data.get("recommendation", "")
                if recommendation:
                    log_output("", "INFO")
                    log_output(f"💡 建议: {recommendation}", "INFO")
            
            # 显示服务器配置
            server_config = status.get("server_config", {})
            if server_config:
                log_output("", "INFO")
                log_output("⚙️  配置信息:", "INFO")
                log_output(f"   连接方式: {server_config.get('connection_type', 'unknown')}", "INFO")
                if server_config.get('description'):
                    log_output(f"   描述: {server_config.get('description')}", "INFO")
                
                docker_icon = "✅" if server_config.get('has_docker', False) else "❌"
                sync_icon = "✅" if server_config.get('has_sync', False) else "❌"
                log_output(f"   Docker支持: {docker_icon}", "INFO")
                log_output(f"   文件同步: {sync_icon}", "INFO")
            
            log_output("", "INFO")
            log_output("🔍 " + "=" * 60, "INFO")
            
        except Exception as e:
            log_output(f"❌ 显示服务器仪表板失败: {str(e)}", "ERROR")
    
    def _show_all_servers_dashboard(self) -> None:
        """显示所有服务器的概览仪表板"""
        try:
            servers = self.list_servers_internal()
            
            if not servers:
                log_output("📭 没有找到配置的服务器", "WARNING")
                return
            
            log_output(f"📊 服务器总数: {len(servers)}", "INFO")
            log_output("", "INFO")
            
            # 统计信息
            connected_count = 0
            healthy_count = 0
            
            for server in servers:
                server_name = server.get('name', 'unknown')
                try:
                    status = self.get_connection_status(server_name)
                    
                    if "error" in status:
                        continue
                    
                    # 基本状态
                    connection_status = status.get("status", "unknown")
                    status_icon = "✅" if connection_status == "connected" else "❌"
                    
                    # 健康状态
                    health_data = status.get("health", {})
                    quality = health_data.get("connection_quality", 0)
                    quality_icon = "🟢" if quality >= 0.8 else "🟡" if quality >= 0.5 else "🔴"
                    
                    if connection_status == "connected":
                        connected_count += 1
                    if quality >= 0.8:
                        healthy_count += 1
                    
                    # 显示服务器信息
                    host = status.get('host', 'unknown')
                    log_output(f"{status_icon} {quality_icon} {server_name:<15} {host:<20} {connection_status}", "INFO")
                    
                except Exception as e:
                    log_output(f"❌ ⚫ {server_name:<15} {'error':<20} 获取状态失败", "ERROR")
            
            log_output("", "INFO")
            log_output(f"📈 连接统计: {connected_count}/{len(servers)} 已连接, {healthy_count}/{len(servers)} 健康", "INFO")
            log_output("", "INFO")
            log_output("🔍 " + "=" * 60, "INFO")
            
        except Exception as e:
            log_output(f"❌ 显示服务器概览失败: {str(e)}", "ERROR")
    
    def monitor_connections_realtime(self, interval: int = 5, duration: int = 60) -> None:
        """实时监控连接状态"""
        try:
            log_output("", "INFO")
            log_output("🔄 " + "=" * 60, "INFO")
            log_output(f"   实时连接监控 (间隔: {interval}秒, 持续: {duration}秒)", "INFO")
            log_output("🔄 " + "=" * 60, "INFO")
            log_output("", "INFO")
            
            start_time = time.time()
            check_count = 0
            
            while time.time() - start_time < duration:
                check_count += 1
                current_time = time.strftime("%H:%M:%S")
                
                log_output(f"📊 监控检查 #{check_count} - {current_time}", "INFO")
                log_output("-" * 50, "INFO")
                
                servers = self.list_servers_internal()
                active_connections = 0
                healthy_connections = 0
                
                for server in servers:
                    server_name = server.get('name', 'unknown')
                    try:
                        # 快速健康检查
                        health_status = self.check_connection_health(server_name)
                        
                        status = health_status.get("status", "unknown")
                        quality = health_status.get("connection_quality", 0)
                        response_time = health_status.get("response_time", 0)
                        
                        # 状态图标
                        if status == "healthy":
                            status_icon = "✅"
                            active_connections += 1
                            if quality >= 0.8:
                                healthy_connections += 1
                        elif status == "unhealthy":
                            status_icon = "⚠️"
                            active_connections += 1
                        elif status == "timeout":
                            status_icon = "⏰"
                        else:
                            status_icon = "❌"
                        
                        quality_bar = self._get_quality_bar(quality)
                        log_output(f"  {status_icon} {server_name:<15} {quality_bar} {response_time:.2f}s", "INFO")
                        
                    except Exception as e:
                        log_output(f"  ❌ {server_name:<15} 检查失败: {str(e)}", "ERROR")
                
                log_output("", "INFO")
                log_output(f"📈 活跃: {active_connections}, 健康: {healthy_connections}", "INFO")
                log_output("", "INFO")
                
                # 等待下一次检查
                if time.time() - start_time < duration - interval:
                    time.sleep(interval)
                else:
                    break
            
            log_output("🔄 实时监控完成", "SUCCESS")
            log_output("🔄 " + "=" * 60, "INFO")
            
        except KeyboardInterrupt:
            log_output("", "INFO")
            log_output("⏹️  监控已停止", "WARNING")
        except Exception as e:
            log_output(f"❌ 实时监控失败: {str(e)}", "ERROR")
    
    def _get_quality_bar(self, quality: float) -> str:
        """生成连接质量进度条"""
        bar_length = 10
        filled = int(quality * bar_length)
        empty = bar_length - filled
        
        if quality >= 0.8:
            bar = "🟢" * filled + "⚫" * empty
        elif quality >= 0.5:
            bar = "🟡" * filled + "⚫" * empty
        else:
            bar = "🔴" * filled + "⚫" * empty
        
        return f"{bar} {quality:.1%}"
    
    def get_connection_summary(self) -> Dict[str, Any]:
        """获取连接状态摘要"""
        try:
            servers = self.list_servers_internal()
            
            summary = {
                "total_servers": len(servers),
                "connected_servers": 0,
                "healthy_servers": 0,
                "unhealthy_servers": 0,
                "error_servers": 0,
                "servers_detail": [],
                "timestamp": time.time()
            }
            
            for server in servers:
                server_name = server.get('name', 'unknown')
                try:
                    status = self.get_connection_status(server_name)
                    
                    if "error" in status:
                        summary["error_servers"] += 1
                        server_detail = {
                            "name": server_name,
                            "status": "error",
                            "quality": 0,
                            "message": status.get("error", "未知错误")
                        }
                    else:
                        connection_status = status.get("status", "unknown")
                        health_data = status.get("health", {})
                        quality = health_data.get("connection_quality", 0)
                        
                        if connection_status == "connected":
                            summary["connected_servers"] += 1
                            
                            if quality >= 0.8:
                                summary["healthy_servers"] += 1
                            else:
                                summary["unhealthy_servers"] += 1
                        
                        server_detail = {
                            "name": server_name,
                            "status": connection_status,
                            "quality": quality,
                            "host": status.get("host", "unknown"),
                            "success_rate": health_data.get("success_rate", 0),
                            "avg_response_time": health_data.get("avg_response_time", 0)
                        }
                    
                    summary["servers_detail"].append(server_detail)
                    
                except Exception as e:
                    summary["error_servers"] += 1
                    summary["servers_detail"].append({
                        "name": server_name,
                        "status": "error",
                        "quality": 0,
                        "message": f"获取状态失败: {str(e)}"
                    })
            
            return summary
            
        except Exception as e:
                         return {
                 "error": f"生成连接摘要失败: {str(e)}",
                 "timestamp": time.time()
             }

    # 🚀 第一阶段优化：错误处理和用户反馈系统
    def diagnose_connection_problem(self, server_name: str, error_message: str = "") -> Dict[str, Any]:
        """诊断连接问题并提供解决方案"""
        try:
            log_output("", "INFO")
            log_output("🔧 " + "=" * 60, "INFO")
            log_output("   连接问题诊断系统", "INFO")
            log_output("🔧 " + "=" * 60, "INFO")
            log_output("", "INFO")
            
            diagnosis = {
                "server_name": server_name,
                "timestamp": time.time(),
                "error_category": "unknown",
                "severity": "medium",
                "diagnosis": "",
                "solutions": [],
                "troubleshooting_steps": [],
                "prevention_tips": []
            }
            
            # 获取服务器信息
            server = self.get_server(server_name)
            if not server:
                diagnosis.update({
                    "error_category": "configuration",
                    "severity": "high",
                    "diagnosis": "服务器配置不存在",
                    "solutions": [
                        "使用 interactive_config_wizard 创建服务器配置",
                        "检查服务器名称是否正确",
                        "验证配置文件是否存在"
                    ],
                    "troubleshooting_steps": [
                        "1. 检查 ~/.remote-terminal/config.yaml 文件",
                        "2. 运行配置向导重新创建服务器配置",
                        "3. 确认服务器名称拼写正确"
                    ]
                })
                self._display_diagnosis(diagnosis)
                return diagnosis
            
            # 分析错误信息
            error_analysis = self._analyze_error_message(error_message)
            diagnosis.update(error_analysis)
            
            # 执行连接测试
            connection_test = self._perform_connection_tests(server)
            diagnosis["connection_tests"] = connection_test
            
            # 生成解决方案
            solutions = self._generate_solutions(server, error_analysis, connection_test)
            diagnosis["solutions"].extend(solutions["solutions"])
            diagnosis["troubleshooting_steps"].extend(solutions["troubleshooting_steps"])
            diagnosis["prevention_tips"].extend(solutions["prevention_tips"])
            
            # 显示诊断结果
            self._display_diagnosis(diagnosis)
            
            return diagnosis
            
        except Exception as e:
            error_diagnosis = {
                "server_name": server_name,
                "error_category": "system",
                "severity": "high",
                "diagnosis": f"诊断系统异常: {str(e)}",
                "solutions": ["重启应用程序", "检查系统权限", "联系技术支持"],
                "timestamp": time.time()
            }
            log_output(f"❌ 诊断失败: {str(e)}", "ERROR")
            return error_diagnosis
    
    def _analyze_error_message(self, error_message: str) -> Dict[str, Any]:
        """分析错误信息并分类"""
        error_message_lower = error_message.lower()
        
        # SSH连接错误
        if any(keyword in error_message_lower for keyword in ["connection refused", "连接被拒绝", "port 22"]):
            return {
                "error_category": "connection_refused",
                "severity": "high",
                "diagnosis": "SSH连接被拒绝 - 目标服务器可能未启动SSH服务或端口被阻塞"
            }
        
        # 认证错误
        elif any(keyword in error_message_lower for keyword in ["authentication failed", "permission denied", "认证失败"]):
            return {
                "error_category": "authentication",
                "severity": "high", 
                "diagnosis": "SSH认证失败 - 用户名、密码或密钥配置错误"
            }
        
        # 网络超时
        elif any(keyword in error_message_lower for keyword in ["timeout", "超时", "network unreachable"]):
            return {
                "error_category": "network_timeout",
                "severity": "medium",
                "diagnosis": "网络连接超时 - 网络不可达或响应缓慢"
            }
        
        # 主机密钥错误
        elif any(keyword in error_message_lower for keyword in ["host key", "known_hosts", "主机密钥"]):
            return {
                "error_category": "host_key",
                "severity": "medium",
                "diagnosis": "SSH主机密钥验证失败 - 主机密钥已更改或不匹配"
            }
        
        # Docker相关错误
        elif any(keyword in error_message_lower for keyword in ["docker", "container", "容器"]):
            return {
                "error_category": "docker",
                "severity": "medium",
                "diagnosis": "Docker容器相关错误 - 容器创建或连接失败"
            }
        
        # Tmux会话错误
        elif any(keyword in error_message_lower for keyword in ["tmux", "session", "会话"]):
            return {
                "error_category": "tmux_session",
                "severity": "low",
                "diagnosis": "Tmux会话管理错误 - 会话创建或连接异常"
            }
        
        # 权限错误
        elif any(keyword in error_message_lower for keyword in ["permission", "权限", "access denied"]):
            return {
                "error_category": "permission",
                "severity": "medium",
                "diagnosis": "权限错误 - 缺少必要的文件或目录访问权限"
            }
        
        # 默认未知错误
        else:
            return {
                "error_category": "unknown",
                "severity": "medium",
                "diagnosis": f"未知错误: {error_message[:100]}..."
            }
    
    def _perform_connection_tests(self, server) -> Dict[str, Any]:
        """执行连接测试"""
        tests = {
            "network_connectivity": {"status": "unknown", "message": ""},
            "ssh_service": {"status": "unknown", "message": ""},
            "authentication": {"status": "unknown", "message": ""},
            "configuration": {"status": "unknown", "message": ""}
        }
        
        try:
            # 网络连通性测试
            import socket
            host = server.host
            port = server.port or 22
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                tests["network_connectivity"] = {
                    "status": "pass",
                    "message": f"网络连接正常 ({host}:{port})"
                }
                tests["ssh_service"] = {
                    "status": "pass", 
                    "message": "SSH服务端口开放"
                }
            else:
                tests["network_connectivity"] = {
                    "status": "fail",
                    "message": f"无法连接到 {host}:{port}"
                }
                tests["ssh_service"] = {
                    "status": "fail",
                    "message": "SSH服务不可访问"
                }
            
        except Exception as e:
            tests["network_connectivity"] = {
                "status": "error",
                "message": f"网络测试异常: {str(e)}"
            }
        
        # 配置验证
        try:
            if hasattr(server, 'username') and server.username:
                if hasattr(server, 'host') and server.host:
                    tests["configuration"] = {
                        "status": "pass",
                        "message": "基本配置完整"
                    }
                else:
                    tests["configuration"] = {
                        "status": "fail",
                        "message": "缺少主机地址配置"
                    }
            else:
                tests["configuration"] = {
                    "status": "fail",
                    "message": "缺少用户名配置"
                }
        except Exception as e:
            tests["configuration"] = {
                "status": "error",
                "message": f"配置验证异常: {str(e)}"
            }
        
        return tests
    
    def _generate_solutions(self, server, error_analysis: Dict, connection_test: Dict) -> Dict[str, Any]:
        """根据错误分析和连接测试生成解决方案"""
        solutions = {
            "solutions": [],
            "troubleshooting_steps": [],
            "prevention_tips": []
        }
        
        error_category = error_analysis.get("error_category", "unknown")
        
        if error_category == "connection_refused":
            solutions["solutions"].extend([
                "🔧 检查目标服务器是否已启动",
                "🔧 验证SSH服务是否正在运行 (sudo systemctl status sshd)",
                "🔧 检查防火墙设置是否阻塞SSH端口",
                "🔧 确认SSH端口配置是否正确"
            ])
            solutions["troubleshooting_steps"].extend([
                "1. 在目标服务器运行: sudo systemctl status sshd",
                "2. 检查防火墙: sudo ufw status 或 sudo firewall-cmd --list-all",
                "3. 验证SSH配置: sudo cat /etc/ssh/sshd_config | grep Port",
                "4. 重启SSH服务: sudo systemctl restart sshd"
            ])
            solutions["prevention_tips"].extend([
                "💡 定期检查SSH服务状态",
                "💡 配置SSH服务自动启动",
                "💡 建立服务器监控机制"
            ])
        
        elif error_category == "authentication":
            solutions["solutions"].extend([
                "🔑 检查用户名是否正确",
                "🔑 验证密码或SSH密钥",
                "🔑 确认用户在目标服务器上存在",
                "🔑 检查SSH密钥权限 (chmod 600 ~/.ssh/id_rsa)"
            ])
            solutions["troubleshooting_steps"].extend([
                "1. 验证用户存在: ssh user@host 'whoami'",
                "2. 检查SSH密钥: ssh-add -l",
                "3. 测试密钥连接: ssh -i ~/.ssh/id_rsa user@host",
                "4. 查看SSH日志: sudo tail -f /var/log/auth.log"
            ])
            solutions["prevention_tips"].extend([
                "💡 使用SSH密钥而非密码认证",
                "💡 定期更新和管理SSH密钥",
                "💡 配置SSH密钥的正确权限"
            ])
        
        elif error_category == "network_timeout":
            solutions["solutions"].extend([
                "🌐 检查网络连接状态",
                "🌐 验证目标主机地址是否正确",
                "🌐 增加连接超时时间",
                "🌐 检查代理或VPN设置"
            ])
            solutions["troubleshooting_steps"].extend([
                "1. 测试网络连通性: ping target_host",
                "2. 检查路由: traceroute target_host",
                "3. 验证DNS解析: nslookup target_host",
                "4. 尝试不同网络环境"
            ])
        
        elif error_category == "host_key":
            solutions["solutions"].extend([
                "🔐 移除旧的主机密钥: ssh-keygen -R hostname",
                "🔐 重新连接以接受新密钥",
                "🔐 验证主机密钥指纹",
                "🔐 更新known_hosts文件"
            ])
            solutions["troubleshooting_steps"].extend([
                "1. 删除旧密钥: ssh-keygen -R " + (server.host if hasattr(server, 'host') else 'hostname'),
                "2. 重新连接: ssh user@host",
                "3. 确认密钥指纹是否正确",
                "4. 检查known_hosts文件: ~/.ssh/known_hosts"
            ])
        
        elif error_category == "docker":
            solutions["solutions"].extend([
                "🐳 检查Docker服务状态",
                "🐳 验证Docker镜像是否存在",
                "🐳 检查容器资源限制",
                "🐳 清理无用的Docker资源"
            ])
            solutions["troubleshooting_steps"].extend([
                "1. 检查Docker状态: docker info",
                "2. 列出镜像: docker images",
                "3. 查看容器: docker ps -a",
                "4. 清理资源: docker system prune"
            ])
        
        # 根据连接测试结果添加特定建议
        if connection_test.get("network_connectivity", {}).get("status") == "fail":
            solutions["solutions"].insert(0, "🚨 优先解决网络连接问题")
        
        if connection_test.get("configuration", {}).get("status") == "fail":
            solutions["solutions"].insert(0, "⚙️ 优先修复配置问题")
        
        return solutions
    
    def _display_diagnosis(self, diagnosis: Dict[str, Any]) -> None:
        """显示诊断结果"""
        try:
            log_output(f"🖥️  服务器: {diagnosis['server_name']}", "INFO")
            log_output(f"📊 错误类别: {diagnosis['error_category']}", "INFO")
            
            # 严重程度显示
            severity = diagnosis.get('severity', 'medium')
            severity_icon = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🟢"
            log_output(f"{severity_icon} 严重程度: {severity}", "INFO")
            
            log_output("", "INFO")
            log_output(f"🔍 诊断结果: {diagnosis['diagnosis']}", "INFO")
            log_output("", "INFO")
            
            # 连接测试结果
            if "connection_tests" in diagnosis:
                log_output("🧪 连接测试结果:", "INFO")
                for test_name, result in diagnosis["connection_tests"].items():
                    status = result.get("status", "unknown")
                    message = result.get("message", "")
                    status_icon = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
                    log_output(f"   {status_icon} {test_name}: {message}", "INFO")
                log_output("", "INFO")
            
            # 解决方案
            if diagnosis.get("solutions"):
                log_output("💡 建议解决方案:", "INFO")
                for i, solution in enumerate(diagnosis["solutions"], 1):
                    log_output(f"   {i}. {solution}", "INFO")
                log_output("", "INFO")
            
            # 故障排查步骤
            if diagnosis.get("troubleshooting_steps"):
                log_output("🔧 详细排查步骤:", "INFO")
                for step in diagnosis["troubleshooting_steps"]:
                    log_output(f"   {step}", "INFO")
                log_output("", "INFO")
            
            # 预防建议
            if diagnosis.get("prevention_tips"):
                log_output("🛡️  预防建议:", "INFO")
                for tip in diagnosis["prevention_tips"]:
                    log_output(f"   {tip}", "INFO")
                log_output("", "INFO")
            
            log_output("🔧 " + "=" * 60, "INFO")
            log_output("", "INFO")
            
        except Exception as e:
            log_output(f"❌ 显示诊断结果失败: {str(e)}", "ERROR")
    
    def show_error_help(self, error_type: str = None) -> None:
        """显示错误类型帮助信息"""
        try:
            log_output("", "INFO")
            log_output("📚 " + "=" * 60, "INFO")
            log_output("   错误处理帮助中心", "INFO")
            log_output("📚 " + "=" * 60, "INFO")
            log_output("", "INFO")
            
            error_help = {
                "connection_refused": {
                    "title": "🚫 连接被拒绝错误",
                    "description": "目标服务器拒绝SSH连接请求",
                    "common_causes": [
                        "SSH服务未启动或已停止",
                        "防火墙阻塞SSH端口",
                        "SSH端口配置错误",
                        "服务器资源不足"
                    ],
                    "quick_fixes": [
                        "重启SSH服务: sudo systemctl restart sshd",
                        "检查端口: sudo netstat -tlnp | grep :22",
                        "开放防火墙: sudo ufw allow ssh"
                    ]
                },
                "authentication": {
                    "title": "🔑 认证失败错误",
                    "description": "SSH用户认证验证失败",
                    "common_causes": [
                        "用户名或密码错误",
                        "SSH密钥配置问题",
                        "用户账户不存在或被锁定",
                        "SSH密钥权限不正确"
                    ],
                    "quick_fixes": [
                        "验证用户名密码",
                        "检查SSH密钥: ssh-add -l",
                        "修复密钥权限: chmod 600 ~/.ssh/id_rsa"
                    ]
                },
                "network_timeout": {
                    "title": "⏰ 网络超时错误",
                    "description": "网络连接超时或不可达",
                    "common_causes": [
                        "网络连接不稳定",
                        "目标主机不可达",
                        "DNS解析问题",
                        "代理或防火墙设置"
                    ],
                    "quick_fixes": [
                        "检查网络连接",
                        "测试连通性: ping target_host",
                        "检查代理设置"
                    ]
                },
                "host_key": {
                    "title": "🔐 主机密钥错误",
                    "description": "SSH主机密钥验证失败",
                    "common_causes": [
                        "主机密钥已更改",
                        "中间人攻击警告",
                        "known_hosts文件损坏",
                        "服务器重新安装"
                    ],
                    "quick_fixes": [
                        "移除旧密钥: ssh-keygen -R hostname",
                        "重新连接接受新密钥",
                        "验证密钥指纹"
                    ]
                }
            }
            
            if error_type and error_type in error_help:
                # 显示特定错误类型的帮助
                help_info = error_help[error_type]
                log_output(help_info["title"], "INFO")
                log_output(f"📝 {help_info['description']}", "INFO")
                log_output("", "INFO")
                
                log_output("🔍 常见原因:", "INFO")
                for cause in help_info["common_causes"]:
                    log_output(f"   • {cause}", "INFO")
                log_output("", "INFO")
                
                log_output("⚡ 快速解决:", "INFO")
                for fix in help_info["quick_fixes"]:
                    log_output(f"   • {fix}", "INFO")
                log_output("", "INFO")
            else:
                # 显示所有错误类型概览
                log_output("🗂️  支持的错误类型:", "INFO")
                log_output("", "INFO")
                
                for error_key, help_info in error_help.items():
                    log_output(f"   {help_info['title']}", "INFO")
                    log_output(f"      {help_info['description']}", "INFO")
                    log_output("", "INFO")
                
                log_output("💡 使用方法:", "INFO")
                log_output("   • 连接失败时自动显示诊断信息", "INFO")
                log_output("   • 使用 diagnose_connection_problem() 手动诊断", "INFO")
                log_output("   • 使用 show_error_help('error_type') 查看特定帮助", "INFO")
                log_output("", "INFO")
            
            log_output("📚 " + "=" * 60, "INFO")
            log_output("", "INFO")
            
        except Exception as e:
            log_output(f"❌ 显示帮助信息失败: {str(e)}", "ERROR")
    
    def create_error_report(self, server_name: str, error_details: Dict) -> str:
        """创建详细的错误报告"""
        try:
            import json
            from datetime import datetime
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "server_name": server_name,
                "error_details": error_details,
                "system_info": {
                    "platform": "remote-terminal-mcp",
                    "version": "0.15.0"
                },
                "server_config": {}
            }
            
            # 获取服务器配置（脱敏）
            server = self.get_server(server_name)
            if server:
                report["server_config"] = {
                    "host": server.host if hasattr(server, 'host') else 'unknown',
                    "port": server.port if hasattr(server, 'port') else 22,
                    "connection_type": getattr(server, 'connection_type', 'ssh'),
                    "has_docker": hasattr(server, 'docker_enabled') and server.docker_enabled,
                    "has_relay": hasattr(server, 'relay_target_host') and server.relay_target_host
                }
            
            # 生成报告文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"error_report_{server_name}_{timestamp}.json"
            
            # 保存报告到临时目录
            import tempfile
            import os
            
            temp_dir = tempfile.gettempdir()
            report_path = os.path.join(temp_dir, report_filename)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            log_output(f"📄 错误报告已生成: {report_path}", "INFO")
            return report_path
            
        except Exception as e:
            log_output(f"❌ 生成错误报告失败: {str(e)}", "ERROR")
            return ""

    def _wait_for_output(self, session_name: str, expected_outputs: List[str], timeout: int) -> bool:
        """等待直到在tmux窗格中看到预期的输出之一。"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                pane_output = subprocess.run(
                    ['tmux', 'capture-pane', '-p', '-t', session_name],
                    capture_output=True, text=True, check=True
                ).stdout
                
                if self._handle_interactive_input(session_name, pane_output):
                    # 如果需要交互，重置计时器
                    start_time = time.time()

                for expected in expected_outputs:
                    if expected in pane_output:
                        return True
            except subprocess.CalledProcessError:
                # 会话可能已关闭
                return False
            time.sleep(1)
        return False


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