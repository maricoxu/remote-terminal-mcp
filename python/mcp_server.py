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

# --- Python Worker Logger ---
log_file_path = os.path.join(os.path.expanduser("~"), ".remote-terminal-mcp-python-worker.log")
with open(log_file_path, "w") as f:
    f.write(f"[{__name__}] Log start for Python worker.\n")

def log_to_file(message):
    with open(log_file_path, "a") as f:
        f.write(f"[{__name__}] {message}\n")

log_to_file(f"Python version: {sys.version}")
log_to_file(f"Current working directory: {os.getcwd()}")
# --- End Logger ---

# -- Robust Startup Logger --
PY_LOG_FILE = Path.home() / 'mcp_service_debug.log'
def startup_log(msg):
    """A simple, robust logger that writes to a file immediately."""
    with open(PY_LOG_FILE, 'a') as f:
        f.write(f"[PYTHON] [{datetime.now().isoformat()}] {msg}\\n")

startup_log("--- Python script started (v0.4.15) ---")

# 设置安静模式，防止SSH Manager显示启动摘要
os.environ['MCP_QUIET'] = '1'
startup_log("MCP_QUIET env var set.")

# 延迟导入
try:
    startup_log("Attempting to import SSHManager...")
    from ssh_manager import SSHManager
    startup_log("SSHManager imported successfully.")
except Exception as e:
    startup_log(f"FATAL: Failed to import SSHManager. Error: {e}\\n{traceback.format_exc()}")
    sys.exit(1)

# 调试模式
DEBUG = os.getenv('MCP_DEBUG', '0') == '1'
startup_log(f"Debug mode is {'ON' if DEBUG else 'OFF'}.")

# 初始化SSH管理器
ssh_manager = None

def get_ssh_manager():
    """获取SSH管理器实例"""
    global ssh_manager
    if ssh_manager is None:
        try:
            startup_log("Attempting to initialize SSHManager...")
            ssh_manager = SSHManager()
            startup_log("SSHManager initialized successfully.")
        except Exception as e:
            startup_log(f"ERROR: Failed to initialize SSHManager. It will be unavailable. Error: {e}\\n{traceback.format_exc()}")
            ssh_manager = None
    return ssh_manager

def debug_log(msg):
    """Logs a message to the debug log file and stderr if not quiet."""
    timestamp = datetime.now().isoformat()
    # Always write to the file
    with open(PY_LOG_FILE, "a") as f:
        f.write(f"[PYTHON] [{timestamp}] {msg}\\n")

    # Only write to stderr if MCP_QUIET is not set
    if os.environ.get("MCP_QUIET") != "1":
        try:
            print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)
        except BrokenPipeError:
            # This can happen if the parent process closes the pipe before we're done writing.
            # It's safe to ignore in this case, as the process is terminating.
            pass

    if DEBUG:
        # Also log to our file for guaranteed capture
        log_to_file(f"DEBUG: {msg}")

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
    
    log_to_file(f"Handling request: method='{method}', id='{request_id}'")
    debug_log(f"Received request: {method} (id: {request_id})")
    
    if request_id is None:
        return # Notification, no response needed
    
    response = None
    try:
        if method == "initialize":
            debug_log("Handling 'initialize' request.")
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "serverInfo": {
                        "name": "remote-terminal-mcp",
                        "version": "0.4.28"
                    }
                }
            }
        
        elif method == "shutdown":
            debug_log("Handling 'shutdown' request.")
            response = { "jsonrpc": "2.0", "id": request_id, "result": {} }
        
        elif method == "tools/list":
            debug_log("Handling 'tools/list' request.")
            tools = get_ssh_manager().list_tools() if get_ssh_manager() else []
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": { "tools": tools }
            }

        elif method == "tools/execute":
            tool_name = params.get("name")
            tool_input = params.get("input", {})
            debug_log(f"Executing tool '{tool_name}' with input: {tool_input}")
            
            manager = get_ssh_manager()
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
            sessions = get_ssh_manager().list_sessions()
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
                success, message = get_ssh_manager().simple_connect(server_name)
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
        send_response(response)

async def main():
    """主事件循环"""
    log_to_file("Starting main event loop.")
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    
    # Send server_ready notification immediately upon startup
    ready_message = {
        "jsonrpc": "2.0",
        "method": "server_ready",
        "params": {} # As a notification, it has no ID
    }
    send_response(ready_message)
    debug_log("Sent server_ready notification.")

    loop = asyncio.get_event_loop()
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    
    log_to_file("Entering main while-loop to process messages.")
    debug_log("Entering main while-loop to process messages.")
    while True:
        try:
            log_to_file("Waiting for line from reader...")
            line_bytes = await reader.readline()
            log_to_file(f"Read {len(line_bytes)} bytes from stdin.")
            if not line_bytes:
                log_to_file("EOF received, sleeping for 1s.")
                await asyncio.sleep(1)
                continue

            line = line_bytes.decode('utf-8').strip()
            log_to_file(f"Decoded line: '{line}'")
            
            if line.startswith("Content-Length:"):
                try:
                    length = int(line.split(":")[1].strip())
                    log_to_file(f"Expecting content length: {length}")
                    
                    await reader.read(2) # Consume the \r\n
                    
                    body_bytes = await reader.read(length)
                    log_to_file(f"Read body with {len(body_bytes)} bytes.")
                    
                    body = body_bytes.decode('utf-8')
                    log_to_file(f"Decoded body: '{body}'")
                    
                    request = json.loads(body)
                    response = await handle_request(request)
                    
                    if response:
                        response_body = json.dumps(response)
                        response_message = f"Content-Length: {len(response_body)}\r\n\r\n{response_body}"
                        
                        sys.stdout.buffer.write(response_message.encode('utf-8'))
                        sys.stdout.flush()
                        log_to_file(f"Sent response for request id {request.get('id')}")

                except json.JSONDecodeError as e:
                    log_to_file(f"JSON Decode Error: {e}. Body was: '{body}'")
                    debug_log(f"JSON Decode Error: {e}. Body was: '{body}'")
                except Exception as e:
                    tb_str = traceback.format_exc()
                    log_to_file(f"Error processing message: {e}\n{tb_str}")
                    debug_log(f"Error processing message: {e}\n{tb_str}")

        except asyncio.CancelledError:
            log_to_file("Main loop cancelled. Shutting down.")
            debug_log("Main loop cancelled. Shutting down.")
            break
        except Exception as e:
            tb_str = traceback.format_exc()
            log_to_file(f"Critical error in main loop: {e}\n{tb_str}")
            debug_log(f"Critical error in main loop: {e}\n{tb_str}")
            await asyncio.sleep(1) # prevent fast crash loop

if __name__ == "__main__":
    try:
        log_to_file("Starting asyncio event loop via __main__.")
        asyncio.run(main())
    except KeyboardInterrupt:
        log_to_file("Service interrupted by user (KeyboardInterrupt).")
        debug_log("Service interrupted by user (KeyboardInterrupt).")
    except Exception as e:
        tb_str = traceback.format_exc()
        log_to_file(f"Unhandled exception in top-level: {e}\n{tb_str}")
        debug_log(f"Unhandled exception in top-level: {e}\n{tb_str}")
    finally:
        log_to_file("Python script is exiting.")