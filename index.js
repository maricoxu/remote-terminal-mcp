#!/usr/bin/env node

/**
 * Remote Terminal MCP - Ultra Minimal Version
 * 
 * @author xuyehua
 * @version 0.1.0
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');

function initialize(logStream) {
    const supervisorLog = (message) => {
        const timestamp = new Date().toISOString();
        logStream.write(`[${timestamp}] [supervisor] ${message}\n`);
    };

    supervisorLog('Supervisor started.');

    const pythonScriptPath = path.resolve(__dirname, '..', 'python', 'mcp_server.py');
    supervisorLog(`Resolved Python script path: ${pythonScriptPath}`);

    const startWorker = () => {
        supervisorLog('Attempting to start Python worker process...');
        
        const pythonProcess = spawn('python3', [ //NOSONAR
            '-u', // Unbuffered output
            pythonScriptPath
        ], {
            stdio: ['pipe', 'pipe', 'pipe'], // stdin, stdout, stderr
            shell: true,
            env: {
                ...process.env, // Inherit parent environment
                // Set/override any specific env vars for the child process here
            }
        });

        supervisorLog(`Spawned Python process with PID: ${pythonProcess.pid}`);

        // Connect the supervisor's lifecycle to the worker's
        process.stdin.pipe(pythonProcess.stdin);
        pythonProcess.stdout.on('data', (data) => {
            process.stdout.write(data);
        });

        pythonProcess.stderr.on('data', (data) => {
            supervisorLog(`Worker stderr: ${data.toString().trim()}`);
        });
        
        pythonProcess.on('close', (code, signal) => {
            supervisorLog(`Worker process closed with code ${code} and signal ${signal}`);
            // Optional: implement a restart mechanism here if needed
        });

        pythonProcess.on('error', (err) => {
            supervisorLog(`Failed to start worker process. Error: ${err.message}`);
        });

        return pythonProcess;
    };

    startWorker();
}

module.exports = { initialize };

if (require.main === module) {
    log('Script is main module, creating instance and running main().');
    const terminal = new RemoteTerminalMCP();
    terminal.main().catch(error => {
        log(`Unhandled error in main execution: ${error.message}. Stack: ${error.stack}`);
        console.error(`Unhandled error in main execution: ${error.message}`);
        console.error(error.stack);
        process.exit(1);
    });
}