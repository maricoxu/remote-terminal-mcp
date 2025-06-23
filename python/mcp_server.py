#!/usr/bin/env python3
"""
Remote Terminal MCP Server

MCP server focused on remote server connections, session management and command execution
"""

import asyncio
import json
import sys
import os
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
import yaml

# 添加项目根目录到路径，以便导入enhanced_config_manager
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from enhanced_config_manager import EnhancedConfigManager
# 修复导入路径 - enhanced_ssh_manager在python目录下
sys.path.insert(0, str(Path(__file__).parent))
from enhanced_ssh_manager import EnhancedSSHManager, log_output, create_enhanced_manager

# 导入colorama用于彩色输出支持
try:
    from colorama import Fore, Style, init
    init()  # 初始化colorama
except ImportError:
    # 如果colorama不可用，创建空的替代
    class Fore:
        CYAN = ""
        GREEN = ""
        RED = ""
        YELLOW = ""
        WHITE = ""
    class Style:
        RESET_ALL = ""

# 服务器信息
SERVER_NAME = "remote-terminal-mcp"
SERVER_VERSION = "0.7.0-mcp-integrated-config"

# 设置安静模式，防止SSH Manager显示启动摘要
os.environ['MCP_QUIET'] = '1'

# 调试模式
DEBUG = os.getenv('MCP_DEBUG', '0') == '1'

def debug_log(msg):
    """改进的调试日志函数，避免stderr输出被误标记为错误"""
    if DEBUG:
        # 只在明确启用调试模式时才输出
        print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)

def info_log(msg):
    """信息级别日志，输出到stderr但不会被误标记"""
    # 使用更温和的信息输出，避免在正常运行时产生错误级别日志
    pass  # 在MCP环境中，我们尽量保持静默

def create_success_response(request_id, text_content):
    """创建一个包含文本内容的成功JSON-RPC响应"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "contentType": "text/plain",
            "content": text_content
        }
    }

def create_error_response(request_id, code, message):
    """创建一个标准的JSON-RPC错误响应"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message
        }
    }

def run_command(cmd, cwd=None, timeout=30):
    """Execute command并返回结果"""
    try:
        debug_log(f"Running command: {cmd}")
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=cwd
        )
        
        output = ""
        if result.stdout:
            output += f"Output:\n{result.stdout}\n"
        if result.stderr:
            output += f"Error output:\n{result.stderr}\n"
        
        output += f"Exit code: {result.returncode}"
        
        return output, result.returncode == 0
        
    except subprocess.TimeoutExpired:
        return f"Command execution timeout ({timeout}s)", False
    except Exception as e:
        return f"Command execution failed: {str(e)}", False

def create_tools_list():
    """创建工具列表，基于SSH Manager的实际功能"""
    return [
        {
            "name": "list_servers",
            "description": "List all available remote servers configured in the system",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "connect_server", 
            "description": "Connect to a remote server by name",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to connect to"
                    }
                },
                "required": ["server_name"]
            }
        },
        {
            "name": "disconnect_server",
            "description": "Disconnect from a remote server and clean up resources",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to disconnect from"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force disconnect even if there are active sessions (default: false)",
                        "default": False
                    }
                },
                "required": ["server_name"]
            }
        },
        {
            "name": "execute_command",
            "description": "Execute a command on a server",
            "inputSchema": {
                "type": "object", 
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    },
                    "server": {
                        "type": "string",
                        "description": "Server name (optional, uses default if not specified)"
                    }
                },
                "required": ["command"]
            }
        },
        {
            "name": "get_server_status",
            "description": "Get connection status of servers",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string", 
                        "description": "Server name (optional, gets all if not specified)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_server_info",
            "description": "Get detailed configuration information for a specific server",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to get detailed information for"
                    }
                },
                "required": ["server_name"]
            }
        },
        {
            "name": "run_local_command",
            "description": "Execute a command on the local system",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "Command to execute locally"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory (optional)"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in seconds (default: 30)"
                    }
                },
                "required": ["cmd"]
            }
        },
        # 配置管理工具 - interactive_config_wizard功能已内置到create/update工具中
        {
            "name": "diagnose_connection",
            "description": "Diagnose connection issues and provide troubleshooting suggestions for a specific server",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to diagnose"
                    },
                    "include_network_test": {
                        "type": "boolean",
                        "description": "Include network connectivity tests (ping, SSH)",
                        "default": True
                    },
                    "include_config_validation": {
                        "type": "boolean",
                        "description": "Include configuration validation",
                        "default": True
                    }
                },
                "required": ["server_name"]
            }
        },
        {
            "name": "create_server_config",
            "description": "🚀 智能服务器配置创建工具 - 支持关键词识别和参数化配置。🌟 新策略：即使提供了参数，也默认进入交互界面（参数作为预填充默认值），确保用户对配置有完全的控制权和可见性。🔍 智能切换：自动检测服务器是否已存在，如存在则自动切换到更新模式。可以通过自然语言描述或直接提供配置参数来创建服务器。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "用户的配置需求描述，支持自然语言。例如：'创建一个新的服务器配置'、'我想添加一台服务器'等"
                    },
                    "name": {
                        "type": "string",
                        "description": "服务器名称（唯一标识符）"
                    },
                    "host": {
                        "type": "string",
                        "description": "服务器主机名或IP地址"
                    },
                    "username": {
                        "type": "string",
                        "description": "SSH连接用户名"
                    },
                    "port": {
                        "type": "integer",
                        "description": "SSH端口号",
                        "default": 22
                    },
                    "connection_type": {
                        "type": "string",
                        "enum": ["ssh", "relay"],
                        "description": "连接类型：ssh（直连）或relay（通过relay-cli）",
                        "default": "ssh"
                    },
                    "description": {
                        "type": "string",
                        "description": "服务器描述信息"
                    },
                    "relay_target_host": {
                        "type": "string",
                        "description": "当使用relay连接时的目标主机"
                    },
                    "docker_enabled": {
                        "type": "boolean",
                        "description": "是否启用Docker容器支持",
                        "default": False
                    },
                    "docker_image": {
                        "type": "string",
                        "description": "Docker镜像名称（当docker_enabled=true时使用）",
                        "default": "ubuntu:20.04"
                    },
                    "docker_container": {
                        "type": "string",
                        "description": "Docker容器名称（当docker_enabled=true时使用）"
                    },
                    "docker_ports": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Docker端口映射列表，格式：[\"host:container\"]，例如：[\"8080:8080\", \"5000:5000\"]",
                        "default": ["8080:8080", "8888:8888", "6006:6006"]
                    },
                    "docker_volumes": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "Docker卷挂载列表，格式：[\"host:container\"]，例如：[\"/home:/home\", \"/data:/data\"]",
                        "default": ["/home:/home", "/data:/data"]
                    },
                    "docker_shell": {
                        "type": "string",
                        "description": "Docker容器内使用的shell，例如：bash, zsh, sh",
                        "default": "bash"
                    },
                    "docker_auto_create": {
                        "type": "boolean",
                        "description": "是否自动创建Docker容器（如果不存在）",
                        "default": True
                    },
                    "auto_detect": {
                        "type": "boolean",
                        "description": "自动检测用户意图",
                        "default": True
                    },
                    "confirm_create": {
                        "type": "boolean",
                        "description": "确认创建配置（当配置完整时使用）",
                        "default": False
                    },
                    "interactive": {
                        "type": "boolean",
                        "description": "是否启用交互式模式。默认true：即使提供了参数也进入交互界面（参数作为默认值）。设置false：跳过交互界面直接创建配置",
                        "default": True
                    },
                    "cursor_interactive": {
                        "type": "boolean",
                        "description": "启用Cursor聊天界面内交互模式（推荐）- 直接在聊天界面显示彩色配置表单，无需切换窗口",
                        "default": False
                    }
                },
                "required": []
            }
        },
        {
            "name": "update_server_config",
            "description": "Update an existing server configuration with new parameters. Includes built-in interactive wizard when no update fields are provided.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to update"
                    },
                    "host": {
                        "type": "string",
                        "description": "Server hostname or IP address"
                    },
                    "username": {
                        "type": "string",
                        "description": "Username for SSH connection"
                    },
                    "port": {
                        "type": "integer",
                        "description": "SSH port"
                    },
                    "connection_type": {
                        "type": "string",
                        "enum": ["ssh", "relay"],
                        "description": "Connection type: ssh (direct) or relay (via relay-cli)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Server description"
                    },
                    "relay_target_host": {
                        "type": "string",
                        "description": "Target host when using relay connection"
                    },
                    "docker_enabled": {
                        "type": "boolean",
                        "description": "Enable Docker container support"
                    },
                    "docker_image": {
                        "type": "string",
                        "description": "Docker image for auto-creation"
                    },
                    "docker_container": {
                        "type": "string",
                        "description": "Docker container name"
                    },
                    "docker_ports": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Docker端口映射列表，格式：[\"host:container\"]，例如：[\"8080:8080\", \"5000:5000\"]",
                        "default": ["8080:8080", "8888:8888", "6006:6006"]
                    },
                    "docker_volumes": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "Docker卷挂载列表，格式：[\"host:container\"]，例如：[\"/home:/home\", \"/data:/data\"]",
                        "default": ["/home:/home", "/data:/data"]
                    },
                    "docker_shell": {
                        "type": "string",
                        "description": "Docker容器内使用的shell，例如：bash, zsh, sh",
                        "default": "bash"
                    },
                    "docker_auto_create": {
                        "type": "boolean",
                        "description": "是否自动创建Docker容器（如果不存在）",
                        "default": True
                    },
                    "show_current_config": {
                        "type": "boolean",
                        "description": "Show current configuration and update guidance (for wizard mode)",
                        "default": True
                    }
                },
                "required": ["server_name"]
            }
        },
        {
            "name": "delete_server_config",
            "description": "Delete a server configuration permanently. This action cannot be undone.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "server_name": {
                        "type": "string",
                        "description": "Name of the server to delete"
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Confirmation flag to prevent accidental deletion (default: false)",
                        "default": False
                    }
                },
                "required": ["server_name"]
            }
        }
    ]

def send_response(response_obj):
    """发送纯JSON响应（兼容Cursor）"""
    try:
        message_str = json.dumps(response_obj)
        # 直接输出JSON，不使用Content-Length头部
        sys.stdout.write(message_str + '\n')
        sys.stdout.flush()
        # 移除debug_log调用，避免stderr输出
        if DEBUG:
            print(f"[DEBUG] Sent JSON response for ID {response_obj.get('id')}", file=sys.stderr, flush=True)
    except BrokenPipeError:
        # 静默处理BrokenPipeError，避免不必要的错误日志
        if DEBUG:
            print("[DEBUG] Failed to send response: Broken pipe. Parent process likely exited.", file=sys.stderr, flush=True)
        pass




async def handle_request(request):
    """处理MCP请求"""
    method = request.get("method", "")
    params = request.get("params")
    request_id = request.get("id")
    
    # 只在调试模式下记录请求信息
    if DEBUG:
        print(f"[DEBUG] Received request: method='{method}', id='{request_id}'", file=sys.stderr, flush=True)
    
    # 处理通知（没有id的请求）
    if request_id is None:
        if method.lower() == "initialized":
            if DEBUG:
                print("[DEBUG] Received 'initialized' notification - handshake complete", file=sys.stderr, flush=True)
            return None
        # 其他通知也直接返回None（不需要响应）
        return None

    try:
        # Normalize method name to be case-insensitive
        method_lower = method.lower()

        if method_lower == "initialize":
            if DEBUG:
                print("[DEBUG] Handling 'initialize' request.", file=sys.stderr, flush=True)
            
            # 完全符合LSP和MCP规范的capabilities
            server_capabilities = {
                "tools": {
                    "listChanged": True
                },
                "resources": {
                    "subscribe": True,
                    "listChanged": True
                },
                "prompts": {
                    "listChanged": True
                },
                "sampling": {}
            }
            
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": server_capabilities,
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION
                    }
                }
            }
            return response
        
        elif method_lower == "shutdown":
            if DEBUG:
                print("[DEBUG] Handling 'shutdown' request.", file=sys.stderr, flush=True)
            response = { "jsonrpc": "2.0", "id": request_id, "result": {} }
            return response
        
        elif method_lower == "tools/list":
            if DEBUG:
                print("[DEBUG] Handling 'tools/list' request.", file=sys.stderr, flush=True)
            tools = create_tools_list()
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": { "tools": tools }
            }
            return response

        elif method_lower == "listofferings":
            if DEBUG:
                print("[DEBUG] Handling 'ListOfferings' request.", file=sys.stderr, flush=True)
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "offerings": []
                }
            }
            return response

        elif method_lower == "tools/call":
            tool_name = params.get("name")
            tool_arguments = params.get("arguments", {})
            # 只在调试模式下记录工具执行信息
            if DEBUG:
                print(f"[DEBUG] Executing tool '{tool_name}' with arguments: {tool_arguments}", file=sys.stderr, flush=True)
            
            try:
                # 统一使用create_enhanced_manager工厂函数
                manager = create_enhanced_manager()  # 使用增强版SSH管理器
                config_manager = EnhancedConfigManager()
                content = ""
                
                if tool_name == "list_servers":
                    # 获取详细的服务器配置信息
                    detailed_servers = []
                    
                    try:
                        # 从配置管理器获取完整配置
                        all_servers = config_manager.get_existing_servers()
                        
                        for server_name, server_config in all_servers.items():
                            # 获取连接状态
                            connection_status = manager.get_connection_status(server_name)
                            
                            # 解析连接类型和跳板信息
                            connection_type = server_config.get('connection_type', 'ssh')
                            is_relay = connection_type == 'relay'
                            
                            # 获取跳板信息
                            jump_info = ""
                            if is_relay:
                                specs = server_config.get('specs', {})
                                connection_specs = specs.get('connection', {})
                                jump_host = connection_specs.get('jump_host', {})
                                if jump_host:
                                    jump_info = f"{jump_host.get('username', 'unknown')}@{jump_host.get('host', 'unknown')}"
                                else:
                                    # 直接relay连接（无跳板）
                                    target = connection_specs.get('target', {})
                                    if target:
                                        jump_info = "直连relay"
                            
                            # 获取Docker配置信息
                            docker_info = ""
                            specs = server_config.get('specs', {})
                            docker_config = specs.get('docker', {})
                            if docker_config:
                                image = docker_config.get('image', '')
                                container = docker_config.get('container_name', '')
                                ports = docker_config.get('ports', [])
                                
                                # 简化镜像名显示
                                if image:
                                    if 'iregistry.baidu-int.com' in image:
                                        image_short = image.split('/')[-1] if '/' in image else image
                                    else:
                                        image_short = image
                                else:
                                    image_short = "未配置"
                                
                                docker_info = f"{image_short}"
                                if container:
                                    docker_info += f" ({container})"
                                if ports:
                                    port_str = ", ".join([str(p) for p in ports[:2]])  # 只显示前2个端口
                                    if len(ports) > 2:
                                        port_str += f"... (+{len(ports)-2})"
                                    docker_info += f" [{port_str}]"
                            
                            # 获取BOS配置信息
                            bos_info = ""
                            bos_config = specs.get('bos', {})
                            if bos_config:
                                bucket = bos_config.get('bucket', '')
                                if bucket:
                                    bos_info = bucket.replace('bos://', '')
                            
                            # 构建详细服务器信息
                            server_detail = {
                                'name': server_name,
                                'description': server_config.get('description', ''),
                                'host': server_config.get('host', ''),
                                'username': server_config.get('username', ''),
                                'port': server_config.get('port', 22),
                                'connection_type': connection_type,
                                'is_relay': is_relay,
                                'jump_info': jump_info,
                                'docker_info': docker_info,
                                'bos_info': bos_info,
                                'connected': connection_status.get('connected', False),
                                'session_name': server_config.get('session', {}).get('name', f"{server_name}_session")
                            }
                            
                            detailed_servers.append(server_detail)
                    
                    except Exception as e:
                        # 如果获取详细信息失败，回退到简单模式
                        servers = manager.list_servers()
                        for server in servers:
                            detailed_servers.append({
                                'name': server.get('name', ''),
                                'description': server.get('description', ''),
                                'connected': server.get('connected', False),
                                'connection_type': 'unknown',
                                'error': f"配置解析失败: {str(e)}"
                            })
                    
                    # 创建美观的表格输出
                    if detailed_servers:
                        content = "🖥️  **远程服务器配置列表**\n\n"
                        
                        for i, server in enumerate(detailed_servers, 1):
                            # 连接状态图标
                            status_icon = "🟢" if server.get('connected') else "🔴"
                            
                            # 连接类型图标
                            if server.get('is_relay'):
                                type_icon = "🔀" if server.get('jump_info') and server.get('jump_info') != "直连relay" else "🔗"
                                type_text = "二级跳板" if server.get('jump_info') and server.get('jump_info') != "直连relay" else "Relay连接"
                            else:
                                type_icon = "🔗"
                                type_text = "直连SSH"
                            
                            content += f"**{i}. {server['name']}** {status_icon}\n"
                            content += f"   📝 {server.get('description', '无描述')}\n"
                            content += f"   {type_icon} **连接方式**: {type_text}\n"
                            content += f"   🎯 **目标**: {server.get('username', '')}@{server.get('host', '')}:{server.get('port', 22)}\n"
                            
                            # 跳板信息
                            if server.get('jump_info') and server.get('jump_info') != "直连relay":
                                content += f"   🚀 **跳板**: {server['jump_info']}\n"
                            
                            # Docker配置
                            if server.get('docker_info'):
                                content += f"   🐳 **Docker**: {server['docker_info']}\n"
                            
                            # BOS配置
                            if server.get('bos_info'):
                                content += f"   ☁️  **BOS**: {server['bos_info']}\n"
                            
                            # 会话信息
                            if server.get('session_name'):
                                content += f"   📺 **会话**: {server['session_name']}\n"
                            
                            content += "\n"
                        
                        # 添加统计信息
                        total_servers = len(detailed_servers)
                        connected_count = sum(1 for s in detailed_servers if s.get('connected'))
                        relay_count = sum(1 for s in detailed_servers if s.get('is_relay'))
                        docker_count = sum(1 for s in detailed_servers if s.get('docker_info'))
                        
                        content += "📊 **统计信息**:\n"
                        content += f"   • 总服务器数: {total_servers}\n"
                        content += f"   • 已连接: {connected_count}/{total_servers}\n"
                        content += f"   • Relay连接: {relay_count}\n"
                        content += f"   • Docker配置: {docker_count}\n"
                    else:
                        content = "📋 暂无配置的服务器"
                    
                elif tool_name == "connect_server":
                    server_name = tool_arguments.get("server_name")
                    if server_name:
                        # 使用增强版智能连接
                        success, message = manager.smart_connect(server_name)
                        if success:
                            # 统一使用EnhancedSSHManager的get_server方法
                            server = manager.get_server(server_name)
                            session_name = server.session.get('name', f"{server_name}_session") if server and server.session else f"{server_name}_session"
                            content = f"✅ 智能连接成功！\n📝 详情: {message}\n\n🎯 连接命令:\ntmux attach -t {session_name}\n\n💡 快速操作:\n• 连接: tmux attach -t {session_name}\n• 分离: Ctrl+B, 然后按 D\n• 查看: tmux list-sessions\n\n🚀 增强功能:\n• 智能连接检测和自动修复\n• 一键式Docker环境连接\n• 交互引导支持"
                        else:
                            content = f"❌ 智能连接失败: {message}"
                    else:
                        content = "Error: server_name parameter is required"
                        
                elif tool_name == "disconnect_server":
                    server_name = tool_arguments.get("server_name")
                    force = tool_arguments.get("force", False)
                    
                    if server_name:
                        try:
                            # 获取服务器信息
                            server = manager.get_server(server_name)
                            if not server:
                                content = json.dumps({
                                    "success": False,
                                    "error": f"Server '{server_name}' not found",
                                    "available_servers": [s.get('name', '') for s in manager.list_servers()]
                                }, ensure_ascii=False, indent=2)
                            else:
                                # 检查连接状态
                                status = manager.get_connection_status(server_name)
                                
                                if not status.get('connected', False):
                                    content = json.dumps({
                                        "success": True,
                                        "message": f"Server '{server_name}' is already disconnected",
                                        "status": "not_connected"
                                    }, ensure_ascii=False, indent=2)
                                else:
                                    # 执行断开连接
                                    disconnect_result = manager.disconnect_server(server_name, force=force)
                                    
                                    if disconnect_result.get('success', False):
                                        content = json.dumps({
                                            "success": True,
                                            "message": f"Successfully disconnected from '{server_name}'",
                                            "details": disconnect_result.get('details', ''),
                                            "cleanup_actions": disconnect_result.get('cleanup_actions', [])
                                        }, ensure_ascii=False, indent=2)
                                    else:
                                        content = json.dumps({
                                            "success": False,
                                            "error": f"Failed to disconnect from '{server_name}': {disconnect_result.get('error', 'Unknown error')}",
                                            "suggestions": disconnect_result.get('suggestions', [])
                                        }, ensure_ascii=False, indent=2)
                        except Exception as e:
                            content = json.dumps({
                                "success": False,
                                "error": f"Exception during disconnect: {str(e)}",
                                "server_name": server_name
                            }, ensure_ascii=False, indent=2)
                    else:
                        content = json.dumps({
                            "success": False,
                            "error": "server_name parameter is required"
                        }, ensure_ascii=False, indent=2)
                        
                elif tool_name == "execute_command":
                    command = tool_arguments.get("command")
                    server = tool_arguments.get("server")
                    if command:
                        result = manager.execute_command(server or "default", command)
                        content = str(result)
                    else:
                        content = "Error: command parameter is required"
                        
                elif tool_name == "get_server_status":
                    server_name = tool_arguments.get("server_name")
                    if server_name:
                        status = manager.get_connection_status(server_name)
                        content = json.dumps(status, ensure_ascii=False, indent=2)
                    else:
                        # 获取所有服务器状态
                        all_status = {}
                        servers = manager.list_servers()
                        for server in servers:
                            server_name = server.get('name')
                            if server_name:
                                all_status[server_name] = manager.get_connection_status(server_name)
                        content = json.dumps(all_status, ensure_ascii=False, indent=2)
                    
                elif tool_name == "get_server_info":
                    server_name = tool_arguments.get("server_name")
                    if server_name:
                        try:
                            # 获取服务器详细配置信息
                            servers = config_manager.get_existing_servers()
                            if server_name in servers:
                                server_info = servers[server_name]
                                # 添加连接状态信息
                                connection_status = manager.get_connection_status(server_name)
                                server_info['connection_status'] = connection_status
                                content = json.dumps(server_info, ensure_ascii=False, indent=2)
                            else:
                                content = json.dumps({
                                    "error": f"Server '{server_name}' not found",
                                    "available_servers": list(servers.keys())
                                }, ensure_ascii=False, indent=2)
                        except Exception as e:
                            content = json.dumps({
                                "error": f"Failed to get server info: {str(e)}"
                            }, ensure_ascii=False, indent=2)
                    else:
                        content = json.dumps({
                            "error": "server_name parameter is required"
                        }, ensure_ascii=False, indent=2)
                
                elif tool_name == "run_local_command":
                    cmd = tool_arguments.get("cmd")
                    cwd = tool_arguments.get("cwd")
                    timeout = tool_arguments.get("timeout", 30)
                    if cmd:
                        output, success = run_command(cmd, cwd, timeout)
                        content = output
                    else:
                        content = "Error: cmd parameter is required"
                
                # interactive_config_wizard功能已内置到create_server_config和update_server_config中
                elif tool_name == "diagnose_connection":
                    server_name = tool_arguments.get("server_name")
                    include_network_test = tool_arguments.get("include_network_test", True)
                    include_config_validation = tool_arguments.get("include_config_validation", True)
                    
                    if server_name:
                        try:
                            # 使用增强版SSH管理器的诊断功能
                            diagnosis = manager.diagnose_connection_problem(server_name)
                            
                            # 如果需要，添加额外的网络测试
                            if include_network_test:
                                diagnosis["network_tests"] = "Network connectivity tests included"
                            
                            if include_config_validation:
                                diagnosis["config_validation"] = "Configuration validation included"
                            
                            content = json.dumps(diagnosis, ensure_ascii=False, indent=2)
                            
                        except Exception as e:
                            content = json.dumps({
                                "error": f"Diagnosis failed: {str(e)}",
                                "server_name": server_name,
                                "suggestions": [
                                    "Verify server name is correct",
                                    "Check if server configuration exists",
                                    "Ensure network connectivity to the server"
                                ]
                            }, ensure_ascii=False, indent=2)
                    else:
                        content = json.dumps({
                            "error": "server_name parameter is required"
                        }, ensure_ascii=False, indent=2)
                
                elif tool_name == "create_server_config":
                    # 🔥 版本标识：2024-06-22 19:25 - 强制交互模式修复版本
                    debug_log("🔥 版本标识：2024-06-22 19:25 - 强制交互模式修复版本")
                    
                    try:
                        # 🎯 获取参数
                        server_name = tool_arguments.get("name", "").strip()
                        server_host = tool_arguments.get("host", "").strip()
                        server_username = tool_arguments.get("username", "").strip()
                        server_port = tool_arguments.get("port", 22)
                        connection_type = tool_arguments.get("connection_type", "relay")  # 默认relay
                        server_description = tool_arguments.get("description", "").strip()
                        relay_target_host = tool_arguments.get("relay_target_host", "").strip()
                        docker_enabled = tool_arguments.get("docker_enabled", True)  # 默认启用Docker
                        docker_image = tool_arguments.get("docker_image", "xmlir_ubuntu_2004_x86_64:v0.32")
                        docker_container = tool_arguments.get("docker_container", "xyh_pytorch")
                        docker_ports = tool_arguments.get("docker_ports", ["8080:8080", "8888:8888", "6006:6006"])
                        docker_volumes = tool_arguments.get("docker_volumes", ["/home:/home", "/data:/data"])
                        docker_shell = tool_arguments.get("docker_shell", "bash")
                        docker_auto_create = tool_arguments.get("docker_auto_create", True)
                        
                        # 调试所有参数
                        debug_log(f"所有tool_arguments: {tool_arguments}")
                        debug_log(f"Docker参数调试:")
                        debug_log(f"  docker_ports: {docker_ports} (type: {type(docker_ports)})")
                        debug_log(f"  docker_volumes: {docker_volumes} (type: {type(docker_volumes)})")
                        debug_log(f"  docker_shell: {docker_shell} (type: {type(docker_shell)})")
                        debug_log(f"  docker_auto_create: {docker_auto_create} (type: {type(docker_auto_create)})")
                        
                        # 🌟 强制交互策略：无论用户输入什么参数，都要跳出交互配置界面
                        # 用户明确要求：不论输入什么都应该跳出交互配置界面
                        
                        # 🎯 强制启动交互配置界面
                        debug_log("🎯 强制启动交互配置界面 - 按用户要求")
                        
                        try:
                            # 创建配置管理器实例
                            config_manager = EnhancedConfigManager()
                            
                            # 准备预填充参数
                            prefill_params = {}
                            if server_name:
                                prefill_params['name'] = server_name
                            if server_host:
                                prefill_params['host'] = server_host
                            if server_username:
                                prefill_params['username'] = server_username
                            if server_port != 22:
                                prefill_params['port'] = server_port
                            if server_description:
                                prefill_params['description'] = server_description
                            if connection_type != 'ssh':
                                prefill_params['connection_type'] = connection_type
                            if docker_enabled:
                                prefill_params['docker_enabled'] = docker_enabled
                            if docker_image != 'ubuntu:20.04':
                                prefill_params['docker_image'] = docker_image
                            if docker_container:
                                prefill_params['docker_container'] = docker_container
                            # 总是包含非默认的Docker参数
                            if docker_ports:
                                prefill_params['docker_ports'] = docker_ports
                            if docker_volumes:
                                prefill_params['docker_volumes'] = docker_volumes
                            if docker_shell:
                                prefill_params['docker_shell'] = docker_shell
                            if docker_auto_create is not None:
                                prefill_params['docker_auto_create'] = docker_auto_create
                            if relay_target_host:
                                prefill_params['relay_target_host'] = relay_target_host
                            
                            # 🎯 新策略：直接启动交互配置界面
                            debug_log("🎯 直接启动交互配置界面 - 用户强烈要求")
                            
                            # 🚀 直接启动向导配置，传递预填充参数
                            try:
                                debug_log("🚀 开始启动向导配置...")
                                result = config_manager.launch_cursor_terminal_config(prefill_params=prefill_params)
                                
                                if result.get("success"):
                                    content = f"✅ **交互配置界面已成功启动**\n\n"
                                    content += f"🎯 **预填充参数已应用**：\n"
                                    for key, value in prefill_params.items():
                                        content += f"  ✅ **{key}**: `{value}`\n"
                                    content += f"\n🌟 **配置界面已在新终端窗口中打开**\n"
                                    content += f"💡 **请查看新打开的终端窗口完成配置**\n"
                                    content += f"🔧 **进程ID**: {result.get('process_id', 'N/A')}\n"
                                    if result.get('prefill_file'):
                                        content += f"📄 **预填充文件**: `{result.get('prefill_file')}`\n"
                                    content += f"\n✨ **配置完成后，您可以通过其他MCP工具连接和管理这个服务器**"
                                    
                                    debug_log("✅ 向导配置启动成功")
                                else:
                                    # 启动失败，提供备用方案
                                    raise Exception(result.get("error", "启动配置界面失败"))
                                
                            except Exception as guided_error:
                                debug_log(f"向导配置异常: {str(guided_error)}")
                                debug_log(f"向导配置异常详情: {traceback.format_exc()}")
                                
                                # 如果直接启动失败，提供备用命令
                                # 生成预填充参数的JSON字符串
                                prefill_json = json.dumps(prefill_params, ensure_ascii=False)
                                
                                content = f"⚠️ **直接启动配置向导遇到问题，请手动启动**\n\n"
                                content += f"**错误**: {str(guided_error)}\n\n"
                                content += f"📋 **您提供的参数将作为默认值预填充**：\n"
                                for key, value in prefill_params.items():
                                    content += f"  ✅ **{key}**: `{value}`\n"
                                content += f"\n🚀 **请复制并运行以下命令**：\n\n"
                                content += f"```bash\n"
                                content += f"cd /Users/xuyehua/Code/remote-terminal-mcp\n"
                                content += f"python3 enhanced_config_manager.py --cursor-terminal\n"
                                content += f"```\n\n"
                                content += f"💡 **操作步骤**：\n"
                                content += f"  1️⃣ **复制上述命令** - 点击代码块右上角的复制按钮\n"
                                content += f"  2️⃣ **打开Cursor内置终端** - 在Cursor界面中打开终端\n"
                                content += f"  3️⃣ **粘贴并运行** - 粘贴命令并按回车键\n"
                                content += f"  4️⃣ **跟随向导** - 按照彩色提示完成配置\n\n"
                                
                                # 创建临时预填充文件
                                import tempfile
                                import os
                                try:
                                    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
                                    temp_file.write(prefill_json)
                                    temp_file.close()
                                    
                                    content += f"🎯 **带预填充参数的命令**（推荐）：\n"
                                    content += f"```bash\n"
                                    content += f"cd /Users/xuyehua/Code/remote-terminal-mcp\n"
                                    content += f"python3 enhanced_config_manager.py --prefill {temp_file.name} --cursor-terminal --auto-close\n"
                                    content += f"```\n\n"
                                    content += f"💡 **预填充文件已创建**: `{temp_file.name}`"
                                    
                                except Exception as temp_error:
                                    debug_log(f"创建临时预填充文件失败: {temp_error}")
                                    content += f"```"
                            
                            debug_log("Successfully generated direct command for user")
                                
                        except Exception as config_error:
                            debug_log(f"交互配置命令生成异常: {str(config_error)}")
                            debug_log(f"交互配置命令生成异常详情: {traceback.format_exc()}")
                            content = f"❌ **交互配置命令生成异常**\n\n"
                            content += f"**错误信息**: {str(config_error)}\n\n"
                            content += f"💡 **手动启动方案**：\n"
                            content += f"```bash\n"
                            content += f"cd /Users/xuyehua/Code/remote-terminal-mcp\n"
                            content += f"python3 enhanced_config_manager.py\n"
                            content += f"```\n\n"
                            content += f"🔍 **详细错误信息**:\n```\n{traceback.format_exc()}\n```"
                            
                    except Exception as e:
                        debug_log(f"Create server config error: {str(e)}")
                        debug_log(f"Create server config traceback: {traceback.format_exc()}")
                        content = json.dumps({
                            "error": f"服务器配置创建失败: {str(e)}"
                        }, ensure_ascii=False, indent=2)
                
                elif tool_name == "update_server_config":
                    try:
                        # 🎯 NEW UPDATE LOGIC 2024-12-22 - 获取参数
                        debug_log("🎯 NEW UPDATE LOGIC: 使用新的update_server_config逻辑！")
                        # 🔥 强制标记：如果看到这个，说明新代码已生效
                        content = "🔥 **新的update_server_config逻辑已生效！** 🔥\n\n"
                        content += f"🎯 **正在更新服务器**: `{tool_arguments.get('server_name', 'unknown')}`\n\n"
                        content += "✅ **代码重新加载成功！新的交互式update逻辑已启用！**\n\n"
                        content += "🚀 **下一步**: 这将启动交互配置界面（功能开发中）"
                        server_name = tool_arguments.get("server_name")
                        if not server_name:
                            content = json.dumps({
                                "error": "server_name parameter is required"
                            }, ensure_ascii=False, indent=2)
                        else:
                            # 🔍 验证服务器是否存在
                            mcp_config_manager = EnhancedConfigManager()
                            servers = mcp_config_manager.get_existing_servers()
                            
                            if server_name not in servers:
                                content = json.dumps({
                                    "error": f"Server '{server_name}' not found",
                                    "available_servers": list(servers.keys())
                                }, ensure_ascii=False, indent=2)
                            else:
                                # 🌟 强制交互策略：与create_server_config保持一致
                                # 无论用户输入什么参数，都要跳出交互配置界面
                                
                                # 🎯 获取当前配置作为基础
                                current_config = servers[server_name].copy()
                                
                                # 🎯 获取更新参数
                                server_host = tool_arguments.get("host", current_config.get("host", ""))
                                server_username = tool_arguments.get("username", current_config.get("username", ""))
                                server_port = tool_arguments.get("port", current_config.get("port", 22))
                                connection_type = tool_arguments.get("connection_type", current_config.get("connection_type", "ssh"))
                                server_description = tool_arguments.get("description", current_config.get("description", ""))
                                relay_target_host = tool_arguments.get("relay_target_host", "")
                                docker_enabled = tool_arguments.get("docker_enabled", 
                                    bool(current_config.get("specs", {}).get("docker")))
                                
                                # 获取当前Docker配置
                                current_docker = current_config.get("specs", {}).get("docker", {})
                                docker_image = tool_arguments.get("docker_image", current_docker.get("image", "ubuntu:20.04"))
                                docker_container = tool_arguments.get("docker_container", 
                                    current_docker.get("container") or current_docker.get("container_name", f"{server_name}_container"))
                                docker_ports = tool_arguments.get("docker_ports", current_docker.get("ports", ["8080:8080", "8888:8888", "6006:6006"]))
                                docker_volumes = tool_arguments.get("docker_volumes", current_docker.get("volumes", ["/home:/home", "/data:/data"]))
                                docker_shell = tool_arguments.get("docker_shell", current_docker.get("shell", "bash"))
                                docker_auto_create = tool_arguments.get("docker_auto_create", current_docker.get("auto_create", True))
                                
                                # 获取当前relay配置
                                current_relay = current_config.get("specs", {}).get("connection", {}).get("target", {})
                                if not relay_target_host and current_relay:
                                    relay_target_host = current_relay.get("host", "")
                                
                                debug_log("🎯 强制启动更新配置界面 - 与create保持一致")
                                
                                try:
                                    # 创建配置管理器实例
                                    config_manager = EnhancedConfigManager()
                                    
                                    # 准备预填充参数（包含当前配置和用户提供的更新）
                                    prefill_params = {
                                        'name': server_name,
                                        'host': server_host,
                                        'username': server_username,
                                        'port': server_port,
                                        'connection_type': connection_type,
                                        'description': server_description or f"更新的{connection_type.upper()}服务器配置",
                                        'docker_enabled': docker_enabled,
                                        'update_mode': True  # 标记为更新模式
                                    }
                                    
                                    # 添加Docker参数
                                    if docker_enabled:
                                        prefill_params.update({
                                            'docker_image': docker_image,
                                            'docker_container': docker_container,
                                            'docker_ports': docker_ports,
                                            'docker_volumes': docker_volumes,
                                            'docker_shell': docker_shell,
                                            'docker_auto_create': docker_auto_create
                                        })
                                    
                                    # 添加relay参数
                                    if connection_type == 'relay' and relay_target_host:
                                        prefill_params['relay_target_host'] = relay_target_host
                                    
                                    # 🎯 新策略：直接启动交互配置界面（更新模式）
                                    debug_log("🎯 直接启动更新配置界面 - 用户强烈要求")
                                    
                                    # 🚀 直接启动向导配置，传递预填充参数
                                    try:
                                        debug_log("🚀 开始启动更新向导配置...")
                                        result = config_manager.launch_cursor_terminal_config(prefill_params=prefill_params)
                                        
                                        if result.get("success"):
                                            content = f"✅ **服务器更新配置界面已成功启动**\n\n"
                                            content += f"🔄 **正在更新服务器**: `{server_name}`\n\n"
                                            content += f"🎯 **当前配置已预填充**：\n"
                                            for key, value in prefill_params.items():
                                                if key != 'update_mode':  # 不显示内部标记
                                                    content += f"  ✅ **{key}**: `{value}`\n"
                                            content += f"\n🌟 **配置界面已在新终端窗口中打开**\n"
                                            content += f"💡 **请查看新打开的终端窗口完成配置更新**\n"
                                            content += f"🔧 **进程ID**: {result.get('process_id', 'N/A')}\n"
                                            if result.get('prefill_file'):
                                                content += f"📄 **预填充文件**: `{result.get('prefill_file')}`\n"
                                            content += f"\n✨ **配置更新完成后，服务器配置将自动保存**"
                                            
                                            debug_log("✅ 更新向导配置启动成功")
                                        else:
                                            # 启动失败，提供备用方案
                                            raise Exception(result.get("error", "启动更新配置界面失败"))
                                        
                                    except Exception as guided_error:
                                        debug_log(f"更新向导配置异常: {str(guided_error)}")
                                        debug_log(f"更新向导配置异常详情: {traceback.format_exc()}")
                                        
                                        # 如果直接启动失败，提供备用命令
                                        # 生成预填充参数的JSON字符串
                                        prefill_json = json.dumps(prefill_params, ensure_ascii=False)
                                        
                                        content = f"⚠️ **直接启动更新配置向导遇到问题，请手动启动**\n\n"
                                        content += f"**错误**: {str(guided_error)}\n\n"
                                        content += f"🔄 **正在更新服务器**: `{server_name}`\n\n"
                                        content += f"📋 **当前配置将作为默认值预填充**：\n"
                                        for key, value in prefill_params.items():
                                            if key != 'update_mode':
                                                content += f"  ✅ **{key}**: `{value}`\n"
                                        content += f"\n🚀 **请复制并运行以下命令**：\n\n"
                                        content += f"```bash\n"
                                        content += f"cd /Users/xuyehua/Code/remote-terminal-mcp\n"
                                        content += f"python3 enhanced_config_manager.py --cursor-terminal\n"
                                        content += f"```\n\n"
                                        content += f"💡 **操作步骤**：\n"
                                        content += f"  1️⃣ **复制上述命令** - 点击代码块右上角的复制按钮\n"
                                        content += f"  2️⃣ **打开Cursor内置终端** - 在Cursor界面中打开终端\n"
                                        content += f"  3️⃣ **粘贴并运行** - 粘贴命令并按回车键\n"
                                        content += f"  4️⃣ **选择更新服务器** - 在向导中选择更新现有服务器\n"
                                        content += f"  5️⃣ **选择{server_name}** - 选择要更新的服务器\n\n"
                                        
                                        # 创建临时预填充文件
                                        import tempfile
                                        import os
                                        try:
                                            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
                                            temp_file.write(prefill_json)
                                            temp_file.close()
                                            
                                            content += f"🎯 **带预填充参数的命令**（推荐）：\n"
                                            content += f"```bash\n"
                                            content += f"cd /Users/xuyehua/Code/remote-terminal-mcp\n"
                                            content += f"python3 enhanced_config_manager.py --prefill {temp_file.name} --cursor-terminal --auto-close\n"
                                            content += f"```\n\n"
                                            content += f"💡 **预填充文件已创建**: `{temp_file.name}`"
                                            
                                        except Exception as temp_error:
                                            debug_log(f"创建临时预填充文件失败: {temp_error}")
                                            content += f"```"
                                    
                                    debug_log("Successfully generated update command for user")
                                        
                                except Exception as config_error:
                                    debug_log(f"更新配置命令生成异常: {str(config_error)}")
                                    debug_log(f"更新配置命令生成异常详情: {traceback.format_exc()}")
                                    content = f"❌ **更新配置命令生成异常**\n\n"
                                    content += f"**错误信息**: {str(config_error)}\n\n"
                                    content += f"💡 **手动启动方案**：\n"
                                    content += f"```bash\n"
                                    content += f"cd /Users/xuyehua/Code/remote-terminal-mcp\n"
                                    content += f"python3 enhanced_config_manager.py\n"
                                    content += f"```\n\n"
                                    content += f"🔍 **详细错误信息**:\n```\n{traceback.format_exc()}\n```"
                                    
                    except Exception as e:
                        debug_log(f"Update server config error: {str(e)}")
                        debug_log(f"Update server config traceback: {traceback.format_exc()}")
                        content = json.dumps({
                            "error": f"服务器配置更新失败: {str(e)}"
                        }, ensure_ascii=False, indent=2)
                
                elif tool_name == "delete_server_config":
                    try:
                        server_name = tool_arguments.get("server_name")
                        confirm = tool_arguments.get("confirm", False)
                        
                        if not server_name:
                            content = json.dumps({
                                "error": "server_name parameter is required"
                            }, ensure_ascii=False, indent=2)
                        elif not confirm:
                            content = json.dumps({
                                "error": "Deletion requires confirmation. Set 'confirm' parameter to true.",
                                "warning": "This action cannot be undone. The server configuration will be permanently deleted."
                            }, ensure_ascii=False, indent=2)
                        else:
                            # 删除服务器配置
                            mcp_config_manager = EnhancedConfigManager()
                            servers = mcp_config_manager.get_existing_servers()
                            
                            if server_name not in servers:
                                content = json.dumps({
                                    "error": f"Server '{server_name}' not found",
                                    "available_servers": list(servers.keys())
                                }, ensure_ascii=False, indent=2)
                            else:
                                try:
                                    # 读取当前配置
                                    import yaml
                                    with open(mcp_config_manager.config_path, 'r', encoding='utf-8') as f:
                                        current_config = yaml.safe_load(f)
                                    
                                    if not current_config:
                                        current_config = {"servers": {}}
                                    
                                    # 删除指定服务器
                                    if "servers" in current_config and server_name in current_config["servers"]:
                                        deleted_config = current_config["servers"][server_name]
                                        del current_config["servers"][server_name]
                                        
                                        # 保存更新后的配置
                                        mcp_config_manager.save_config(current_config, merge_mode=False)
                                        
                                        content = json.dumps({
                                            "success": True,
                                            "message": f"Server '{server_name}' deleted successfully",
                                            "deleted_config": deleted_config,
                                            "remaining_servers": list(current_config.get("servers", {}).keys())
                                        }, ensure_ascii=False, indent=2)
                                    else:
                                        content = json.dumps({
                                            "error": f"Server '{server_name}' not found in configuration"
                                        }, ensure_ascii=False, indent=2)
                                        
                                except Exception as delete_error:
                                    content = json.dumps({
                                        "error": f"Failed to delete server config: {str(delete_error)}"
                                    }, ensure_ascii=False, indent=2)
                                    
                    except Exception as e:
                        content = json.dumps({
                            "error": f"Failed to delete server config: {str(e)}"
                        }, ensure_ascii=False, indent=2)
                
                elif tool_name == "diagnose_connection":
                    server_name = tool_arguments.get("server_name")
                    
                    if not server_name:
                        content = "Error: server_name is required for diagnosis"
                    else:
                        try:
                            # 使用配置管理器的测试连接功能
                            result = config_manager.test_connection()
                            content = f"🔍 连接诊断功能已启动，请在配置管理界面中选择服务器 '{server_name}' 进行测试"
                        except Exception as e:
                            content = f"❌ 启动连接诊断失败: {str(e)}"
                
                else:
                    content = f"Unknown tool: {tool_name}"
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": content
                            }
                        ]
                    }
                }
                
            except Exception as e:
                debug_log(f"Tool execution error: {e}\n{traceback.format_exc()}")
                response = create_error_response(request_id, -32603, f"Error executing tool '{tool_name}': {e}")
            
            return response

        else:
            response = create_error_response(request_id, -32601, f"Unknown method: {method}")
            return response
            
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        debug_log(f"{error_msg}\n{traceback.format_exc()}")
        response = create_error_response(request_id, -32603, error_msg)
        return response

async def main():
    """主事件循环"""
    if DEBUG:
        print(f"[DEBUG] Starting MCP Python Server v{SERVER_VERSION}", file=sys.stderr, flush=True)
    
    loop = asyncio.get_event_loop()

    # 1. 设置异步读取器 (stdin)
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    if DEBUG:
        print("[DEBUG] Entering main while-loop to process messages.", file=sys.stderr, flush=True)
    while True:
        try:
            line_bytes = await reader.readline()
            if not line_bytes:
                await asyncio.sleep(1) # prevent busy-looping on closed stdin
                continue

            line = line_bytes.decode('utf-8').strip()
            
            if not line:
                continue

            try:
                request = json.loads(line)
                response = await handle_request(request)
                
                if response:
                    # 发送纯JSON响应
                    send_response(response)

            except json.JSONDecodeError as e:
                debug_log(f"JSON Decode Error: {e}. Body was: '{line}'")
            except Exception as e:
                debug_log(f"Error processing line: {e}")
                debug_log(traceback.format_exc())

        except asyncio.CancelledError:
            debug_log("Main loop cancelled.")
            break
        except Exception as e:
            debug_log(f"Critical error in main loop: {e}")
            debug_log(traceback.format_exc())
            # In case of a critical error, sleep a bit to prevent a tight error loop
            await asyncio.sleep(1)

if __name__ == "__main__":
    # 检查是否是测试模式
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("🧪 MCP服务器测试模式")
        try:
            # 测试导入
            from enhanced_config_manager import EnhancedConfigManager
            from enhanced_ssh_manager import EnhancedSSHManager
            print("✅ 所有模块导入成功")
            
            # 测试配置管理器
            config_manager = EnhancedConfigManager()
            servers = config_manager.get_existing_servers()
            print(f"✅ 配置管理器工作正常，发现 {len(servers)} 个服务器")
            
            # 测试SSH管理器
            # 统一使用create_enhanced_manager工厂函数
            ssh_manager = create_enhanced_manager()
            print("✅ SSH管理器初始化成功")
            
            print("🎉 所有测试通过！MCP服务器可以正常启动")
            sys.exit(0)
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        debug_log("Server shut down by KeyboardInterrupt.")
    except Exception as e:
        tb_str = traceback.format_exc()
        debug_log(f"Unhandled exception in top-level: {e}\n{tb_str}")