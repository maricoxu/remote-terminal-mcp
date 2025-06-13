#!/usr/bin/env node

/**
 * Real npm MCP Server - Direct Python Call
 * 
 * @author xuyehua
 * @version 0.4.57
 */

const { spawn } = require('child_process');
const path = require('path');

// 直接启动Python MCP服务器，无需supervisor
const pythonScriptPath = path.resolve(__dirname, 'python', 'mcp_server.py');

const pythonProcess = spawn('python3', ['-u', pythonScriptPath], {
    stdio: 'inherit',  // 直接继承父进程的stdio
    env: { 
        ...process.env, 
        PYTHONUNBUFFERED: '1',
        MCP_NPM_VERSION: '1'  // 标识这是npm版本
    }
});

pythonProcess.on('close', (code) => {
    process.exit(code);
});

pythonProcess.on('error', (err) => {
    console.error('Failed to start Python MCP server:', err);
    process.exit(1);
});

// 处理进程退出
process.on('SIGINT', () => {
    pythonProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
    pythonProcess.kill('SIGTERM');
}); 