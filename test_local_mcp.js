#!/usr/bin/env node

/**
 * 本地MCP服务器测试脚本
 * 用于验证MCP服务器功能是否正常
 */

const { spawn } = require('child_process');
const path = require('path');

console.log('🚀 启动本地MCP服务器测试');
console.log('=' * 50);

function testMCPServer() {
    const mcpServerPath = path.resolve(__dirname, 'index.js');
    console.log(`📁 MCP服务器路径: ${mcpServerPath}`);
    
    // 启动MCP服务器
    const serverProcess = spawn('node', [mcpServerPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: {
            ...process.env,
            MCP_DEBUG: '1',
            MCP_LOCAL_MODE: 'true'
        }
    });

    console.log(`🔧 MCP服务器PID: ${serverProcess.pid}`);

    // 监听输出
    serverProcess.stdout.on('data', (data) => {
        console.log(`[MCP输出] ${data.toString().trim()}`);
    });

    serverProcess.stderr.on('data', (data) => {
        console.log(`[MCP错误] ${data.toString().trim()}`);
    });

    // 发送测试请求
    setTimeout(() => {
        console.log('\n📤 发送测试请求');
        
        const testRequest = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        };

        serverProcess.stdin.write(JSON.stringify(testRequest) + '\n');
    }, 2000);

    // 15秒后停止测试
    setTimeout(() => {
        console.log('\n⏰ 测试完成，停止服务器');
        serverProcess.kill('SIGTERM');
        process.exit(0);
    }, 15000);

    serverProcess.on('error', (err) => {
        console.error(`❌ MCP服务器启动失败: ${err.message}`);
        process.exit(1);
    });

    serverProcess.on('exit', (code, signal) => {
        console.log(`🔚 MCP服务器已退出. 代码: ${code}, 信号: ${signal}`);
    });
}

// 运行测试
testMCPServer(); 