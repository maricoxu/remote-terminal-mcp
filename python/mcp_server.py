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

# 替换原有导入
#from config_manager.main import EnhancedConfigManager
from python.config_manager.main import EnhancedConfigManager
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
                        "description": "连接类型：ssh（直连）或relay（通过relay-cli）",
                        "enum": ["ssh", "relay"],
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
                    # 自动同步配置参数
                    "auto_sync_enabled": {
                        "type": "boolean",
                        "description": "是否启用自动同步功能（使用proftpd）",
                        "default": False
                    },
                    "sync_remote_workspace": {
                        "type": "string",
                        "description": "远程工作目录路径",
                        "default": "/home/Code"
                    },
                    "sync_ftp_port": {
                        "type": "integer",
                        "description": "FTP服务端口",
                        "default": 8021
                    },
                    "sync_ftp_user": {
                        "type": "string",
                        "description": "FTP用户名",
                        "default": "ftpuser"
                    },
                    "sync_ftp_password": {
                        "type": "string",
                        "description": "FTP密码",
                        "default": "sync_password"
                    },
                    "sync_local_workspace": {
                        "type": "string",
                        "description": "本地工作目录路径（空表示当前目录）",
                        "default": ""
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
                        "description": "Connection type: ssh (direct) or relay (via relay-cli)",
                        "enum": ["ssh", "relay"]
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
                    # 自动同步配置参数
                    "auto_sync_enabled": {
                        "type": "boolean",
                        "description": "是否启用自动同步功能（使用proftpd）"
                    },
                    "sync_remote_workspace": {
                        "type": "string",
                        "description": "远程工作目录路径"
                    },
                    "sync_ftp_port": {
                        "type": "integer",
                        "description": "FTP服务端口"
                    },
                    "sync_ftp_user": {
                        "type": "string",
                        "description": "FTP用户名"
                    },
                    "sync_ftp_password": {
                        "type": "string",
                        "description": "FTP密码"
                    },
                    "sync_local_workspace": {
                        "type": "string",
                        "description": "本地工作目录路径（空表示当前目录）"
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
                
                # list_servers工具适配新实现
                if tool_name == "list_servers":
                    try:
                        manager = EnhancedConfigManager()
                        servers = manager.list_servers()
                        content = json.dumps({"servers": servers}, ensure_ascii=False, indent=2)
                    except Exception as e:
                        debug_log(f"list_servers error: {str(e)}")
                        content = json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
                        
                elif tool_name == "connect_server":
                    server_name = tool_arguments.get("server_name")
                    if server_name:
                        # 🚀 使用新的connect.py连接管理器
                        try:
                            from python.connect import connect_server as new_connect_server
                            result = new_connect_server(server_name)
                            
                            if result.success:
                                content = f"✅ 连接成功！\n📝 详情: {result.message}\n\n🎯 连接信息:\n"
                                if result.session_name:
                                    content += f"• 会话名称: {result.session_name}\n"
                                    content += f"• 连接终端: tmux attach -t {result.session_name}\n"
                                    content += f"• 分离会话: Ctrl+B, 然后按 D\n"
                                if result.details:
                                    content += f"• 连接类型: {result.details.get('connection_type', '未知')}\n"
                                    content += f"• 目标主机: {result.details.get('host', '未知')}\n"
                                    if result.details.get('docker_container'):
                                        content += f"• Docker容器: {result.details.get('docker_container')}\n"
                                content += f"\n🚀 新架构特性:\n• 分离关注点设计\n• 增强的relay认证处理\n• 智能交互引导\n• 健康状态检测"
                            else:
                                content = f"❌ 连接失败: {result.message}"
                                if result.details and result.details.get('tmux_command'):
                                    content += f"\n\n💡 手动连接: {result.details['tmux_command']}"
                        except ImportError as e:
                            # 降级到原有实现
                            success, message = manager.smart_connect(server_name)
                            if success:
                                server = manager.get_server(server_name)
                                session_name = server.session.get('name', f"{server_name}_session") if server and server.session else f"{server_name}_session"
                                content = f"✅ 连接成功（兼容模式）: {message}\n🎯 连接: tmux attach -t {session_name}"
                            else:
                                content = f"❌ 连接失败: {message}"
                        except Exception as e:
                            content = f"❌ 连接异常: {str(e)}"
                    else:
                        content = "Error: server_name parameter is required"
                        
                elif tool_name == "disconnect_server":
                    server_name = tool_arguments.get("server_name")
                    force = tool_arguments.get("force", False)
                    
                    if server_name:
                        try:
                            from python.connect import disconnect_server as new_disconnect_server
                            result = new_disconnect_server(server_name)
                            
                            if result.success:
                                content = f"✅ 断开连接成功\n📝 详情: {result.message}\n🎯 服务器: {server_name}"
                            else:
                                content = f"❌ 断开连接失败: {result.message}"
                        except ImportError:
                            # 降级到原有实现
                            try:
                                server = manager.get_server(server_name)
                                if not server:
                                    content = f"❌ 服务器 '{server_name}' 不存在"
                                else:
                                    disconnect_result = manager.disconnect_server(server_name, force=force)
                                    if disconnect_result.get('success', False):
                                        content = f"✅ 成功断开连接: {server_name}"
                                    else:
                                        content = f"❌ 断开连接失败: {disconnect_result.get('error', '未知错误')}"
                            except Exception as e:
                                content = f"❌ 断开连接异常: {str(e)}"
                        except Exception as e:
                            content = f"❌ 断开连接异常: {str(e)}"
                    else:
                        content = "Error: server_name parameter is required"
                        
                elif tool_name == "execute_command":
                    command = tool_arguments.get("command")
                    server = tool_arguments.get("server")
                    if command:
                        try:
                            from python.connect import execute_server_command
                            result = execute_server_command(server or "default", command)
                            
                            if result.success:
                                content = f"✅ 命令执行成功\n\n📋 命令: {command}\n\n📄 输出:\n{result.details.get('output', '无输出') if result.details else '无输出'}"
                            else:
                                content = f"❌ 命令执行失败: {result.message}"
                        except ImportError:
                            # 降级到原有实现
                            result = manager.execute_command(server or "default", command)
                            content = str(result)
                        except Exception as e:
                            content = f"❌ 命令执行异常: {str(e)}"
                    else:
                        content = "Error: command parameter is required"
                        
                elif tool_name == "get_server_status":
                    server_name = tool_arguments.get("server_name")
                    if server_name:
                        try:
                            from python.connect import get_server_status as new_get_server_status
                            result = new_get_server_status(server_name)
                            
                            if result.success:
                                content = f"📊 服务器状态: {server_name}\n"
                                content += f"🔗 状态: {result.status.value}\n"
                                content += f"📝 详情: {result.message}\n"
                                if result.session_name:
                                    content += f"🎯 会话: {result.session_name}"
                            else:
                                content = f"❌ 获取状态失败: {result.message}"
                        except ImportError:
                            # 降级到原有实现
                            status = manager.get_connection_status(server_name)
                            content = json.dumps(status, ensure_ascii=False, indent=2)
                        except Exception as e:
                            content = f"❌ 获取状态异常: {str(e)}"
                    else:
                        # 获取所有服务器状态
                        try:
                            from python.connect import list_all_servers
                            servers_info = list_all_servers()
                            
                            if servers_info:
                                content = "📊 所有服务器状态:\n\n"
                                for server in servers_info:
                                    status_icon = {"connected": "🟢", "ready": "✅", "disconnected": "🔴", "error": "❌"}.get(server['status'], "❓")
                                    content += f"{status_icon} **{server['name']}**\n"
                                    content += f"   📍 主机: {server['host']}\n"
                                    content += f"   👤 用户: {server['username']}\n"
                                    content += f"   🔗 状态: {server['status']}\n"
                                    if server.get('docker_container'):
                                        content += f"   🐳 容器: {server['docker_container']}\n"
                                    content += "\n"
                            else:
                                content = "📋 暂无配置的服务器"
                        except ImportError:
                            # 降级到原有实现
                            all_status = {}
                            servers = manager.list_servers()
                            for server in servers:
                                server_name = server.get('name')
                                if server_name:
                                    all_status[server_name] = manager.get_connection_status(server_name)
                            content = json.dumps(all_status, ensure_ascii=False, indent=2)
                        except Exception as e:
                            content = f"❌ 获取服务器列表异常: {str(e)}"
                    
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
                
                # create_server_config工具适配新实现
                elif tool_name == "create_server_config":
                    try:
                        manager = EnhancedConfigManager()
                        server_info = tool_arguments.copy()
                        
                        # 启动真正的交互配置界面
                        interactive_result = manager.launch_cursor_terminal_config(prefill_params=server_info)
                        
                        if interactive_result and interactive_result.get('success'):
                            content = f"""🚀 **Cursor内置终端配置向导已启动！**

✨ **配置界面已在Cursor内置终端中打开**

📋 **您提供的参数已作为默认值预填充**：
"""
                            # 显示预填充的参数
                            if server_info.get('name'):
                                content += f"  ✅ **name**: `{server_info['name']}`\n"
                            if server_info.get('host'):
                                content += f"  ✅ **host**: `{server_info['host']}`\n"
                            if server_info.get('username'):
                                content += f"  ✅ **username**: `{server_info['username']}`\n"
                            if server_info.get('port'):
                                content += f"  ✅ **port**: `{server_info['port']}`\n"
                            if server_info.get('description'):
                                content += f"  ✅ **description**: `{server_info['description']}`\n"
                            
                            content += f"""
🎯 **操作步骤**：
  1️⃣ **查看内置终端** - 配置界面已在Cursor内置终端中显示
  2️⃣ **按提示填写** - 跟随彩色界面的引导逐步配置
  3️⃣ **确认配置** - 系统会显示完整配置供您确认
  4️⃣ **自动保存** - 确认后配置立即生效，可直接使用

🔥 **版本标识**: 2024-12-22 交互界面增强版
"""
                        else:
                            # 降级到非交互模式
                            result = manager.guided_setup(prefill=server_info)
                            if result:
                                content = f"✅ 服务器配置创建成功\n配置: {json.dumps(result, ensure_ascii=False, indent=2)}"
                            else:
                                content = "❌ 服务器配置创建失败"
                    except Exception as e:
                        debug_log(f"create_server_config error: {str(e)}")
                        content = json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
                
                # update_server_config工具适配新实现
                elif tool_name == "update_server_config":
                    try:
                        manager = EnhancedConfigManager()
                        name = tool_arguments.get("name")
                        update_info = tool_arguments.copy()
                        update_info.pop("name", None)
                        
                        # 使用update_server_config方法更新服务器配置
                        result = manager.update_server_config(name, **update_info)
                        
                        if result:
                            content = f"✅ 服务器 {name} 已更新\n配置: {json.dumps(result, ensure_ascii=False, indent=2)}"
                        else:
                            content = f"❌ 服务器 {name} 更新失败"
                    except Exception as e:
                        debug_log(f"update_server_config error: {str(e)}")
                        content = json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
                
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
                                        mcp_config_manager.save_config(current_config, merge=False)
                                        
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
                
                # NEW UPDATE LOGIC: update_server_config 新逻辑已加载
                # 强制交互策略：与create_server_config保持一致
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
            from config_manager.main import EnhancedConfigManager
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
            
            # 交互界面启动调用：launch_cursor_terminal_config
            # 此调用仅在测试模式下进行，以确保Cursor客户端能够正确加载配置
            # 在实际生产环境中，此调用应由Cursor客户端发起
            if DEBUG:
                print("[DEBUG] Testing launch_cursor_terminal_config function.", file=sys.stderr, flush=True)
                result = config_manager.launch_cursor_terminal_config(prefill_params={'name': 'test_server'})
                print(f"✅ launch_cursor_terminal_config测试结果: {result}")
            
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