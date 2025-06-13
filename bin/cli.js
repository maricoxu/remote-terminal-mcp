#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

/**
 * Final, truly robust entry point for the remote-terminal-mcp executable.
 * This version installs a global uncaught exception handler, which is the
 * ultimate tool to debug mysterious crashes during Node.js process startup.
 *
 * @version 0.6.1 - Fixed NPM Package Path Resolution
 */

const errorLogPath = path.join(require('os').homedir(), 'mcp_UNCAUGHT_EXCEPTION.log');
const debugLogPath = path.join(require('os').homedir(), 'mcp_DEBUG.log');

// 创建日志函数
function createLogger() {
    return function log(message) {
        const timestamp = new Date().toISOString();
        const logMessage = `[${timestamp}] [cli.js] ${message}\n`;
        
        // 同时输出到控制台和文件
        console.error(logMessage.trim());
        fs.appendFileSync(debugLogPath, logMessage);
    };
}

const log = createLogger();

// The ultimate safety net: Catch ANY exception that isn't handled anywhere else.
process.on('uncaughtException', (error) => {
    const timestamp = new Date().toISOString();
    const errorMessage = `[${timestamp}] [cli.js] GLOBAL UNCAUGHT EXCEPTION:\nName: ${error.name}\nMessage: ${error.message}\nStack: ${error.stack}\n`;
    
    // Synchronously write to the log file. This is critical.
    fs.appendFileSync(errorLogPath, errorMessage);
    log(`FATAL: Uncaught exception - ${error.message}`);
    
    // It's generally recommended to exit after an uncaught exception.
    process.exit(1);
});

log('=== CLI Starting ===');
log(`Process ID: ${process.pid}`);
log(`Working directory: ${process.cwd()}`);
log(`Script directory: ${__dirname}`);
log(`Script filename: ${__filename}`);

// 智能NPM包路径解析 - 修复版本
function findPythonScript() {
    // 检测是否在NPM包环境中
    const isNpmPackage = __dirname.includes('node_modules') || __dirname.includes('_npx') || process.cwd().includes('node_modules');
    log(`NPM package environment detected: ${isNpmPackage}`);
    log(`Current working directory: ${process.cwd()}`);
    log(`__dirname: ${__dirname}`);
    
    // 可能的Python脚本路径
    const possiblePaths = [];
    
    if (isNpmPackage) {
        // NPM包环境的路径策略
        possiblePaths.push(
            // 1. 相对于当前bin目录 (标准NPM包结构)
            path.join(__dirname, '..', 'python', 'mcp_server.py'),
            // 2. 相对于工作目录 (npx执行时)
            path.join(process.cwd(), 'python', 'mcp_server.py'),
            // 3. 在node_modules中的包结构
            path.resolve(__dirname, '..', 'python', 'mcp_server.py'),
            // 4. 查找包根目录
            path.join(__dirname, '..', '..', 'python', 'mcp_server.py'),
            // 5. 从当前工作目录向上查找
            path.join(process.cwd(), '..', 'python', 'mcp_server.py')
        );
    } else {
        // 开发环境的路径策略
        possiblePaths.push(
            // 1. 相对于bin目录 (开发环境)
            path.join(__dirname, '..', 'python', 'mcp_server.py'),
            // 2. 绝对路径查找
            path.resolve(__dirname, '..', 'python', 'mcp_server.py')
        );
    }
    
    for (const pythonPath of possiblePaths) {
        log(`Testing Python path: ${pythonPath}`);
        if (fs.existsSync(pythonPath)) {
            log(`✅ Found Python script at: ${pythonPath}`);
            return pythonPath;
        } else {
            log(`❌ Path not found: ${pythonPath}`);
        }
    }
    
    log('❌ Could not find Python script in any expected location');
    
    // 最后的尝试：递归搜索
    if (isNpmPackage) {
        log('Attempting recursive search...');
        const searchRoots = [
            process.cwd(),
            path.resolve(__dirname, '..'),
            path.resolve(__dirname, '..', '..')
        ];
        
        for (const root of searchRoots) {
            const searchPath = path.join(root, 'python', 'mcp_server.py');
            log(`Recursive search path: ${searchPath}`);
            if (fs.existsSync(searchPath)) {
                log(`✅ Found via recursive search: ${searchPath}`);
                return searchPath;
            }
        }
    }
    
    return null;
}

// Now, we can safely attempt to load the main application logic.
try {
    log('Loading main module...');
    
    // 首先找到Python脚本
    const pythonScriptPath = findPythonScript();
    if (!pythonScriptPath) {
        throw new Error('Python script not found');
    }
    
    // 创建一个自定义的initialize函数，传入正确的Python路径
    function customInitialize(logFunction) {
        const { spawn } = require('child_process');
        
        logFunction('--- Node.js Supervisor/Worker Initializing ---');
        logFunction(`Attempting to start Python worker at: ${pythonScriptPath}`);
        
        // 启动Python进程
        const pythonProcess = spawn('python3', ['-u', pythonScriptPath], {
            stdio: ['pipe', 'pipe', 'pipe']
        });
        
        logFunction(`Spawned Python process with PID: ${pythonProcess.pid}`);
        logFunction('Supervisor is now proxying I/O to the Python worker.');
        
        // 设置I/O代理
        process.stdin.pipe(pythonProcess.stdin);
        pythonProcess.stdout.pipe(process.stdout);
        
        pythonProcess.stderr.on('data', (data) => {
            const message = data.toString().trim();
            if (message) {
                logFunction(`[Python stderr] ${message}`);
            }
        });
        
        // 处理进程退出
        pythonProcess.on('exit', (code, signal) => {
            logFunction(`Python process exited with code ${code}, signal ${signal}`);
            process.exit(code || 0);
        });
        
        // 处理错误
        pythonProcess.on('error', (error) => {
            logFunction(`Python process error: ${error.message}`);
            process.exit(1);
        });
    }
    
    log('Calling custom initialize function...');
    customInitialize(log);
    
} catch (error) {
    log(`FATAL: Failed to load or initialize main module - ${error.message}`);
    log(`Stack: ${error.stack}`);
    process.exit(1);
} 