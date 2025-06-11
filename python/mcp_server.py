#!/usr/bin/env python3
"""
Remote Terminal MCP Server

MCP server focused on remote server connections, session management and command execution
"""

import asyncio
import json
import sys
import os
import traceback
from pathlib import Path
from datetime import datetime

# 设置安静模式，防止SSH Manager显示启动摘要
os.environ['MCP_QUIET'] = '1'

# 延迟导入
try:
    from ssh_manager import SSHManager
except Exception as e:
    print(f"FATAL: Failed to import SSHManager. Error: {e}\\n{traceback.format_exc()}")
    sys.exit(1)

# 调试模式
DEBUG = os.getenv('MCP_DEBUG', '0') == '1'

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
    """创建Error响应"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": error_code,
            "message": error_message
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
                return "Current tmux sessions:\n" + '\n'.join(f"  • {session}" for session in sessions)
            else:
                return "No active tmux sessions"
        else:
            return "Cannot access tmux (not installed or not running)"
            
    except FileNotFoundError:
        return "tmux not installed"
    except Exception as e:
        return f"Failed to list tmux sessions: {str(e)}"

def check_system_info():
    """检查系统信息"""
    info = []
    
    # 操作系统信息
    try:
        import platform
        info.append(f"System: {platform.system()} {platform.release()}")
        info.append(f"Hostname: {platform.node()}")
        info.append(f"Architecture: {platform.machine()}")
    except Exception as e:
        info.append(f"Cannot get system info: {e}")
    
    # 当前目录
    try:
        cwd = os.getcwd()
        info.append(f"Current directory: {cwd}")
    except Exception as e:
        info.append(f"Cannot get current directory: {e}")
    
    # 用户信息
    try:
        import getpass
        user = getpass.getuser()
        info.append(f"Current user: {user}")
    except Exception as e:
        info.append(f"Cannot get user info: {e}")
    
    return "\n".join(info)

def send_response(response_obj):
    """Sends a JSON-RPC response object to stdout."""
    try:
        message_str = json.dumps(response_obj)
        header = f"Content-Length: {len(message_str)}\\r\\n\\r\\n"
        
        # Ensure all parts are sent to stdout
        sys.stdout.write(header)
        sys.stdout.write(message_str)
        sys.stdout.flush()
        debug_log(f"Sent response for ID {response_obj.get('id')}")
    except BrokenPipeError:
        # Parent process has likely exited, cannot send response.
        debug_log("Failed to send response: Broken pipe. Parent process likely exited.")
        pass # Ignore error as we are likely shutting down

async def handle_request(request):
    """处理MCP请求"""
    method = request.get("method", "")
    request_id = request.get("id")
    params = request.get("params", {})
    
    debug_log(f"Received request: method='{method}', id='{request_id}'")
    
    if request_id is None:
        return None
    
    response = None
    try:
        if method == "initialize":
            debug_log("Handling 'initialize' request.")
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": True,
                        "prompts": True,
                        "resources": {
                            "listChanged": False
                        },
                        "logging": {
                            "log": True
                        }
                    },
                    "serverInfo": {
                        "name": "remote-terminal-mcp",
                        "version": "0.4.40"
                    }
                }
            }
        
        elif method == "shutdown":
            debug_log("Handling 'shutdown' request.")
            response = { "jsonrpc": "2.0", "id": request_id, "result": {} }
        
        elif method == "tools/list":
            debug_log("Handling 'tools/list' request.")
            tools = SSHManager().list_tools()
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": { "tools": tools }
            }

        elif method == "tools/execute":
            tool_name = params.get("name")
            tool_input = params.get("input", {})
            debug_log(f"Executing tool '{tool_name}' with input: {tool_input}")
            
            manager = SSHManager()
            if not manager:
                response = create_error_response(request_id, "SSH Manager is not available.")
            else:
                try:
                    content = manager.execute_tool(tool_name, tool_input)
                    response = create_success_response(request_id, content)
                except Exception as e:
                    debug_log(f"Tool execution error: {e}\\n{traceback.format_exc()}")
                    response = create_error_response(request_id, f"Error executing tool '{tool_name}': {e}")

        elif method == "list_sessions":
            sessions = SSHManager().list_sessions()
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": { "sessions": sessions }
            }

        elif method == "connect_server":
            server_name = params.get("server_name")
            if not server_name:
                response = create_error_response(request_id, "Missing parameter: server_name", -32602)
            else:
                success, message = SSHManager().simple_connect(server_name)
                if success:
                    response = create_success_response(request_id, message)
                else:
                    response = create_error_response(request_id, message, -32000)

        elif method == "run_command":
            cmd = params.get("cmd")
            cwd = params.get("cwd")
            timeout = params.get("timeout", 30)
            output, success = run_command(cmd, cwd, timeout)
            response = create_success_response(request_id, output) if success else create_error_response(request_id, output)

        else:
            response = create_error_response(request_id, f"Unknown method: {method}", -32601)
            
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        debug_log(f"{error_msg}\\n{traceback.format_exc()}")
        response = create_error_response(request_id, error_msg)

    if response:
        debug_log(f"Sent response for ID {request.get('id')}")
        # The main loop now handles sending the response
        return response
    return None

async def main():
    """主事件循环"""
    debug_log("Starting main event loop.")
    
    loop = asyncio.get_event_loop()

    # 1. 设置异步读取器 (stdin)
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    # 2. 设置异步写入器 (stdout) - 这是架构正确的做法
    writer_transport, writer_protocol = await loop.connect_write_pipe(
        lambda: asyncio.streams.FlowControlMixin(loop=loop), sys.stdout
    )
    writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, loop)

    # 发送一个 "server_ready" 通知，这可能是某些客户端需要的
    try:
        ready_notification = {
            "jsonrpc": "2.0",
            "method": "server_ready",
            "params": {}
        }
        body = json.dumps(ready_notification)
        message = f"{body}\n"
        writer.write(message.encode('utf-8'))
        await writer.drain()
        debug_log("Sent server_ready notification.")
    except Exception as e:
        debug_log(f"Failed to send server_ready notification: {e}")

    debug_log("Entering main while-loop to process messages.")
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
                    response_body = json.dumps(response)
                    response_message = f"{response_body}\n"
                    
                    writer.write(response_message.encode('utf-8'))
                    await writer.drain()

            except json.JSONDecodeError as e:
                debug_log(f"JSON Decode Error: {e}. Body was: '{line}'")
            except Exception as e:
                tb_str = traceback.format_exc()
                debug_log(f"Error processing message: {e}\n{tb_str}")

        except asyncio.CancelledError:
            debug_log("Main loop cancelled. Shutting down.")
            break
        except Exception as e:
            tb_str = traceback.format_exc()
            debug_log(f"Critical error in main loop: {e}\n{tb_str}")
            await asyncio.sleep(1) # prevent fast crash loop

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        debug_log("Service interrupted by user (KeyboardInterrupt).")
    except Exception as e:
        tb_str = traceback.format_exc()
        debug_log(f"Unhandled exception in top-level: {e}\n{tb_str}")