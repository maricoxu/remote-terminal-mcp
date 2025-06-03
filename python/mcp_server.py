#!/usr/bin/env python3
"""
Remote Terminal MCP Server - 远程终端管理

专注于远程服务器连接、会话管理和命令执行的MCP服务器
"""

import asyncio
import json
import sys
import os
import subprocess
import time

# 调试模式
DEBUG = os.getenv('MCP_DEBUG') == '1'

def debug_log(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)

def create_success_response(request_id, text_content):
    """创建成功响应"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": text_content
                }
            ]
        }
    }

def create_error_response(request_id, error_message, error_code=-32603):
    """创建错误响应"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": error_code,
            "message": error_message
        }
    }

def run_command(cmd, cwd=None, timeout=30):
    """执行命令并返回结果"""
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
            output += f"📤 输出:\n{result.stdout}\n"
        if result.stderr:
            output += f"⚠️ 错误输出:\n{result.stderr}\n"
        
        output += f"🔢 退出码: {result.returncode}"
        
        return output, result.returncode == 0
        
    except subprocess.TimeoutExpired:
        return f"⏱️ 命令执行超时 ({timeout}秒)", False
    except Exception as e:
        return f"❌ 命令执行失败: {str(e)}", False

def list_tmux_sessions():
    """列出tmux会话"""
    try:
        result = subprocess.run(
            ['tmux', 'list-sessions'], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            sessions = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    sessions.append(line)
            
            if sessions:
                return "🖥️ 当前tmux会话:\n" + '\n'.join(f"  • {session}" for session in sessions)
            else:
                return "📭 没有活动的tmux会话"
        else:
            return "❌ 无法访问tmux (可能未安装或未运行)"
            
    except FileNotFoundError:
        return "❌ tmux未安装"
    except Exception as e:
        return f"❌ 列出tmux会话失败: {str(e)}"

def check_system_info():
    """检查系统信息"""
    info = []
    
    # 操作系统信息
    try:
        import platform
        info.append(f"🖥️ 系统: {platform.system()} {platform.release()}")
        info.append(f"🏷️ 主机名: {platform.node()}")
        info.append(f"⚙️ 架构: {platform.machine()}")
    except Exception as e:
        info.append(f"❌ 无法获取系统信息: {e}")
    
    # 当前目录
    try:
        cwd = os.getcwd()
        info.append(f"📁 当前目录: {cwd}")
    except Exception as e:
        info.append(f"❌ 无法获取当前目录: {e}")
    
    # 用户信息
    try:
        import getpass
        user = getpass.getuser()
        info.append(f"👤 当前用户: {user}")
    except Exception as e:
        info.append(f"❌ 无法获取用户信息: {e}")
    
    return "\n".join(info)

async def handle_request(request):
    """处理MCP请求"""
    method = request.get("method", "")
    request_id = request.get("id")
    
    debug_log(f"Received method: {method}, id: {request_id}")
    
    # 如果没有id，这是一个通知，不需要响应
    if request_id is None:
        debug_log(f"Received notification: {method}, no response needed")
        if method.startswith("notifications/"):
            debug_log(f"Handling notification: {method}")
        return None
    
    # 处理需要响应的请求
    if method == "initialize":
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {
                    "name": "remote-terminal-mcp",
                    "version": "0.2.0"
                }
            }
        }
        debug_log(f"Initialize response: {json.dumps(response)}")
        return response
        
    elif method == "tools/list":
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "system_info",
                        "description": "获取系统信息和当前状态",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "run_command",
                        "description": "执行本地命令",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": "要执行的命令"
                                },
                                "working_directory": {
                                    "type": "string",
                                    "description": "执行命令的工作目录"
                                },
                                "timeout": {
                                    "type": "integer",
                                    "description": "命令超时时间（秒）",
                                    "default": 30
                                }
                            },
                            "required": ["command"]
                        }
                    },
                    {
                        "name": "list_tmux_sessions",
                        "description": "列出当前的tmux会话",
                        "inputSchema": {
                            "type": "object",
                            "properties": {}
                        }
                    },
                    {
                        "name": "create_tmux_session",
                        "description": "创建新的tmux会话",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "session_name": {
                                    "type": "string",
                                    "description": "会话名称"
                                },
                                "working_directory": {
                                    "type": "string",
                                    "description": "会话的工作目录"
                                }
                            },
                            "required": ["session_name"]
                        }
                    },
                    {
                        "name": "list_directory",
                        "description": "列出目录内容",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                    "description": "要列出的目录路径",
                                    "default": "."
                                },
                                "show_hidden": {
                                    "type": "boolean",
                                    "description": "是否显示隐藏文件",
                                    "default": False
                                }
                            }
                        }
                    }
                ]
            }
        }
        debug_log(f"Tools list response: {json.dumps(response)}")
        return response
        
    elif method == "tools/call":
        # 处理工具调用
        tool_name = request.get("params", {}).get("name", "")
        arguments = request.get("params", {}).get("arguments", {})
        
        debug_log(f"Tool call: {tool_name}, arguments: {arguments}")
        
        if tool_name == "system_info":
            try:
                info = check_system_info()
                return create_success_response(request_id, info)
            except Exception as e:
                debug_log(f"Error in system_info: {e}")
                return create_error_response(request_id, f"获取系统信息失败: {str(e)}")
        
        elif tool_name == "run_command":
            try:
                command = arguments.get("command", "")
                working_directory = arguments.get("working_directory")
                timeout = arguments.get("timeout", 30)
                
                if not command:
                    return create_error_response(request_id, "命令不能为空")
                
                output, success = run_command(command, working_directory, timeout)
                
                result_text = f"🔧 执行命令: {command}\n"
                if working_directory:
                    result_text += f"📁 工作目录: {working_directory}\n"
                result_text += f"\n{output}"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in run_command: {e}")
                return create_error_response(request_id, f"命令执行失败: {str(e)}")
        
        elif tool_name == "list_tmux_sessions":
            try:
                sessions = list_tmux_sessions()
                return create_success_response(request_id, sessions)
            except Exception as e:
                debug_log(f"Error in list_tmux_sessions: {e}")
                return create_error_response(request_id, f"列出tmux会话失败: {str(e)}")
        
        elif tool_name == "create_tmux_session":
            try:
                session_name = arguments.get("session_name", "")
                working_directory = arguments.get("working_directory", "")
                
                if not session_name:
                    return create_error_response(request_id, "会话名称不能为空")
                
                # 构建tmux命令
                cmd = f"tmux new-session -d -s '{session_name}'"
                if working_directory:
                    cmd += f" -c '{working_directory}'"
                
                output, success = run_command(cmd)
                
                if success:
                    result_text = f"✅ 成功创建tmux会话: {session_name}\n"
                    if working_directory:
                        result_text += f"📁 工作目录: {working_directory}\n"
                    result_text += f"\n💡 使用 'tmux attach -t {session_name}' 连接到会话"
                else:
                    result_text = f"❌ 创建tmux会话失败:\n{output}"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in create_tmux_session: {e}")
                return create_error_response(request_id, f"创建tmux会话失败: {str(e)}")
        
        elif tool_name == "list_directory":
            try:
                path = arguments.get("path", ".")
                show_hidden = arguments.get("show_hidden", False)
                
                # 构建ls命令
                cmd = "ls -la" if show_hidden else "ls -l"
                cmd += f" '{path}'"
                
                output, success = run_command(cmd)
                
                if success:
                    result_text = f"📁 目录内容: {path}\n\n{output}"
                else:
                    result_text = f"❌ 无法列出目录内容:\n{output}"
                
                return create_success_response(request_id, result_text)
                
            except Exception as e:
                debug_log(f"Error in list_directory: {e}")
                return create_error_response(request_id, f"列出目录失败: {str(e)}")
        
        else:
            return create_error_response(request_id, f"未知工具: {tool_name}", -32601)
            
    else:
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": "Method not supported"
            }
        }
        debug_log(f"Error response: {json.dumps(response)}")
        return response

async def main():
    """主函数"""
    debug_log("Starting Remote Terminal MCP server...")
    
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                debug_log("No more input, exiting...")
                break
            
            if line.strip():
                debug_log(f"Received input: {line.strip()}")
                request = json.loads(line.strip())
                response = await handle_request(request)
                
                # 只有当有响应时才输出
                if response is not None:
                    output = json.dumps(response)
                    debug_log(f"Sending output: {output}")
                    print(output, flush=True)
                
        except Exception as e:
            debug_log(f"Error processing request: {e}")
            continue

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        debug_log("Received interrupt, exiting...")
        pass