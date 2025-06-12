#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

/**
 * Final, truly robust entry point for the remote-terminal-mcp executable.
 * This version installs a global uncaught exception handler, which is the
 * ultimate tool to debug mysterious crashes during Node.js process startup.
 *
 * @version 0.4.52
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

// Now, we can safely attempt to load the main application logic.
try {
    log('Loading main module...');
    const { initialize } = require('../index.js');
    
    log('Calling initialize function...');
    initialize(log);
    
} catch (error) {
    log(`FATAL: Failed to load or initialize main module - ${error.message}`);
    log(`Stack: ${error.stack}`);
    process.exit(1);
} 