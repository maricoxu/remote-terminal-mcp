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

function initialize(log) {
    log('--- Node.js Supervisor/Worker Initializing ---');

    function startWorker() {
        const pythonScriptPath = path.resolve(__dirname, 'python', 'mcp_server.py');
        log(`Attempting to start Python worker at: ${pythonScriptPath}`);
        
        const pythonProcess = spawn('python3', [
            '-u', // Unbuffered stdout/stderr
            pythonScriptPath
        ], {
            stdio: 'pipe',
            env: { ...process.env, MCP_DEBUG: '1' }
        });

        log(`Spawned Python process with PID: ${pythonProcess.pid || 'N/A'}`);

        process.stdin.pipe(pythonProcess.stdin);
        pythonProcess.stdout.pipe(process.stdout);
        pythonProcess.stderr.on('data', (data) => {
            log(`[Python stderr] ${data.toString().trim()}`);
        });

        const onProcessExit = (code, signal) => {
            log(`Python worker exited. Code: ${code}, Signal: ${signal}. Supervisor will exit.`);
            process.exit(code === null ? 1 : code);
        };
        
        pythonProcess.on('close', onProcessExit);
        pythonProcess.on('error', (err) => {
            log(`FATAL: Failed to start Python worker. Error: ${err.message}`);
            process.exit(1);
        });

        process.on('exit', () => {
             log('Supervisor is exiting, ensuring worker is terminated.');
             pythonProcess.kill();
        });

        log('Supervisor is now proxying I/O to the Python worker.');
    }

    try {
        startWorker();
    } catch (e) {
        log(`FATAL: An unhandled error occurred during worker startup. ${e.message}`);
        process.exit(1);
    }
}

module.exports = { initialize };