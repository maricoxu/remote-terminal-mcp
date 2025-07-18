#!/usr/bin/env python3
"""
MCP测试工具类

为回归测试提供MCP工具调用的标准化接口
遵循MCP优先原则，所有功能测试都通过MCP工具完成
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import tempfile
import os


class MCPTestClient:
    """MCP测试客户端，用于在测试中调用MCP工具"""
    
    def __init__(self, mcp_server_path: Optional[str] = None):
        """
        初始化MCP测试客户端
        
        Args:
            mcp_server_path: MCP服务器脚本路径，默认使用项目中的python/mcp_server.py
        """
        if mcp_server_path is None:
            project_root = Path(__file__).parent.parent.parent
            mcp_server_path = project_root / "mcp_server.py"
        
        self.mcp_server_path = Path(mcp_server_path)
        self.request_id = 0
        
    def _get_next_request_id(self) -> int:
        """获取下一个请求ID"""
        self.request_id += 1
        return self.request_id
        
    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> Any:
        """
        调用MCP工具
        
        Args:
            tool_name: 工具名称 (如: list_servers, connect_server, execute_command)
            arguments: 工具参数字典
            timeout: 超时时间（秒），默认10秒
            
        Returns:
            工具执行结果
            
        Raises:
            MCPTestError: 当工具调用失败时
        """
        if arguments is None:
            arguments = {}
            
        # 构造MCP请求
        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_request_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            # 启动MCP服务器进程
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    sys.executable, str(self.mcp_server_path),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, "MCP_QUIET": "1"}
                ),
                timeout=5.0  # 进程启动超时5秒
            )
            
            # 发送请求并等待响应（带超时）
            request_data = json.dumps(request) + "\n"
            stdout, stderr = await asyncio.wait_for(
                process.communicate(request_data.encode()),
                timeout=timeout
            )
            
            # 解析响应
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "MCP服务器进程异常退出"
                raise MCPTestError(f"MCP服务器错误: {error_msg}")
                
            response_text = stdout.decode().strip()
            if not response_text:
                raise MCPTestError("MCP服务器没有返回响应")
                
            # 解析JSON响应
            try:
                response = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise MCPTestError(f"无法解析MCP响应: {e}\n响应内容: {response_text}")
                
            # 检查错误
            if "error" in response:
                error = response["error"]
                raise MCPTestError(f"MCP工具调用失败: {error.get('message', '未知错误')}")
                
            # 返回结果
            return response.get("result", {}).get("content", response.get("result"))
            
        except asyncio.TimeoutError:
            # 超时处理
            if 'process' in locals():
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                except:
                    process.kill()
            raise MCPTestError(f"MCP工具调用超时 ({timeout}秒): {tool_name}")
            
        except Exception as e:
            if isinstance(e, MCPTestError):
                raise
            raise MCPTestError(f"调用MCP工具时发生异常: {str(e)}")
            
    async def list_servers(self) -> List[Dict[str, Any]]:
        """获取服务器列表"""
        return await self.call_tool("list_servers")
        
    async def connect_server(self, server_name: str) -> str:
        """连接到指定服务器"""
        return await self.call_tool("connect_server", {"server_name": server_name})
        
    async def disconnect_server(self, server_name: str, force: bool = False) -> str:
        """断开服务器连接"""
        return await self.call_tool("disconnect_server", {
            "server_name": server_name,
            "force": force
        })
        
    async def execute_command(self, command: str, server: Optional[str] = None) -> str:
        """在服务器上执行命令"""
        params = {"command": command}
        if server:
            params["server"] = server
        return await self.call_tool("execute_command", params)
        
    async def get_server_status(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """获取服务器状态"""
        params = {}
        if server_name:
            params["server_name"] = server_name
        return await self.call_tool("get_server_status", params)
        
    async def get_server_info(self, server_name: str) -> Dict[str, Any]:
        """获取服务器详细信息"""
        return await self.call_tool("get_server_info", {"server_name": server_name})
        
    async def diagnose_connection(self, server_name: str, 
                                include_network_test: bool = True,
                                include_config_validation: bool = True) -> str:
        """诊断连接问题"""
        return await self.call_tool("diagnose_connection", {
            "server_name": server_name,
            "include_network_test": include_network_test,
            "include_config_validation": include_config_validation
        })


class MCPTestError(Exception):
    """MCP测试异常"""
    pass


class MCPTestEnvironment:
    """MCP测试环境管理器"""
    
    def __init__(self):
        """初始化测试环境"""
        self.temp_config_dir = None
        self.original_config_path = None
        
    async def __aenter__(self):
        """进入测试环境"""
        # 创建临时配置目录
        self.temp_config_dir = tempfile.mkdtemp(prefix="mcp_test_")
        
        # 备份原始配置路径
        self.original_config_path = os.environ.get("MCP_CONFIG_PATH")
        
        # 设置测试配置路径
        os.environ["MCP_CONFIG_PATH"] = self.temp_config_dir
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出测试环境"""
        # 恢复原始配置路径
        if self.original_config_path is not None:
            os.environ["MCP_CONFIG_PATH"] = self.original_config_path
        elif "MCP_CONFIG_PATH" in os.environ:
            del os.environ["MCP_CONFIG_PATH"]
            
        # 清理临时目录
        if self.temp_config_dir and Path(self.temp_config_dir).exists():
            import shutil
            shutil.rmtree(self.temp_config_dir)
            
    def create_test_config(self, server_name: str, config: Dict[str, Any]):
        """创建测试用的服务器配置"""
        config_file = Path(self.temp_config_dir) / f"{server_name}.yaml"
        
        # 生成YAML配置内容
        yaml_content = self._dict_to_yaml(config)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
            
        return config_file
        
    def _dict_to_yaml(self, data: Dict[str, Any], indent: int = 0) -> str:
        """简单的字典到YAML转换（避免依赖yaml库）"""
        lines = []
        for key, value in data.items():
            prefix = "  " * indent
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._dict_to_yaml(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    lines.append(f"{prefix}  - {item}")
            else:
                lines.append(f"{prefix}{key}: {value}")
        return "\n".join(lines)


# 便利函数，用于快速创建测试实例
def create_mcp_test_client() -> MCPTestClient:
    """创建MCP测试客户端实例"""
    return MCPTestClient()


def create_test_environment() -> MCPTestEnvironment:
    """创建MCP测试环境实例"""
    return MCPTestEnvironment() 