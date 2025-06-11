#!/usr/bin/env node

/**
 * Remote Terminal MCP - Ultra Minimal Version
 * 
 * @author xuyehua
 * @version 0.1.0
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

// 1. 日志系统先行
const logFilePath = path.join(require('os').homedir(), 'mcp_supervisor_debug.log');
const logStream = fs.createWriteStream(logFilePath, { flags: 'a' });

function supervisorLog(message) {
    const timestamp = new Date().toISOString();
    logStream.write(`[${timestamp}] [supervisor] ${message}\\n`);
    // 在调试时，也输出到控制台
    if (process.env.MCP_DEBUG === '1') {
        console.error(`[supervisor] ${message}`);
    }
}

supervisorLog('--- Node.js Supervisor script started (v0.4.33) ---');

// 2. 核心：启动并管理Python子进程
function startWorker() {
    const pythonScriptPath = path.resolve(__dirname, 'python', 'mcp_server.py');
    supervisorLog(`Resolved Python script path: ${pythonScriptPath}`);
    
    supervisorLog('Attempting to start Python worker process...');
    
    const pythonProcess = spawn('python3', [
        '-u', // Unbuffered stdout/stderr
        pythonScriptPath
    ], {
        stdio: 'pipe', // 确保我们能控制stdin, stdout, stderr
        env: { ...process.env } // 传递环境变量
    });

    supervisorLog(`Spawned Python process with PID: ${pythonProcess.pid || 'N/A'}`);

    // 3. 建立双向管道
    process.stdin.pipe(pythonProcess.stdin);
    pythonProcess.stdout.pipe(process.stdout);

    // 4. 健壮的事件监听
    process.stdin.on('close', () => {
        supervisorLog('Supervisor stdin has been closed. Terminating worker.');
        pythonProcess.kill();
    });

    pythonProcess.stderr.on('data', (data) => {
        supervisorLog(`WORKER STDERR: ${data.toString().trim()}`);
    });

    pythonProcess.on('close', (code, signal) => {
        supervisorLog(`Worker process exited. Code: ${code}, Signal: ${signal}.`);
        // 当子进程退出时，主进程也退出
        process.exit(code || 1);
    });

    pythonProcess.on('error', (err) => {
        supervisorLog(`FATAL: Failed to start worker process. Error: ${err.message}`);
        process.exit(1);
    });

    supervisorLog('Supervisor is now proxying I/O to the worker process.');
}

// 5. 直接执行核心逻辑
try {
    startWorker();
} catch (e) {
    supervisorLog(`FATAL: An unhandled error occurred in the supervisor. ${e.message}`);
    process.exit(1);
}