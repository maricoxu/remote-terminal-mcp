#!/usr/bin/env python3
"""
简单的MCP测试服务器，使用官方MCP库
"""

import asyncio
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions, NotificationOptions
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.types as types

# 创建服务器实例
server = Server("remote-terminal-test")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """返回可用工具列表"""
    return [
        Tool(
            name="test_tool",
            description="测试工具",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "测试消息"
                    }
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="system_info",
            description="获取系统信息",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """处理工具调用"""
    if name == "test_tool":
        message = arguments.get("message", "Hello")
        return [TextContent(type="text", text=f"✅ 测试成功！收到消息: {message}")]
    
    elif name == "system_info":
        import platform
        import os
        info = f"""
🖥️ 系统信息:
  • 系统: {platform.system()} {platform.release()}
  • 主机名: {platform.node()}
  • 当前目录: {os.getcwd()}
  • Python版本: {platform.python_version()}
        """
        return [TextContent(type="text", text=info.strip())]
    
    else:
        raise ValueError(f"未知工具: {name}")

async def main():
    """主函数"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="remote-terminal-test",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main()) 