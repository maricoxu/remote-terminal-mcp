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

    supervisorLog('Supervisor logic initiated.');

    process.stdin.on('error', (err) => {
        supervisorLog(`SUPERVISOR STDIN ERROR: ${err.message}`);
    });
    process.stdin.on('close', () => {
        supervisorLog('SUPERVISOR STDIN CLOSED. Worker will be terminated.');
    });

    const pythonScriptPath = path.resolve(__dirname, 'python', 'mcp_server.py');
    supervisorLog(`Resolved Python script path: ${pythonScriptPath}`);

    const startWorker = () => {
        supervisorLog('Attempting to start Python worker process...');
        
        const pythonProcess = spawn('python3', [
            '-u', 
            pythonScriptPath
        ], {
            stdio: 'pipe',
            shell: true,
            env: process.env,
        });

        supervisorLog(`Spawned Python process with PID: ${pythonProcess.pid || 'N/A'}`);

        // Full stream connection with diagnostic logging
        try {
            process.stdin.pipe(pythonProcess.stdin);
            supervisorLog('Pipe established: Supervisor stdin -> Worker stdin');
        } catch (e) {
            supervisorLog(`FATAL: Failed to pipe stdin: ${e.message}`);
        }

        try {
            pythonProcess.stdout.pipe(process.stdout);
            supervisorLog('Pipe established: Worker stdout -> Supervisor stdout');
        } catch (e) {
            supervisorLog(`FATAL: Failed to pipe stdout: ${e.message}`);
        }
        
        pythonProcess.stderr.on('data', (data) => {
            supervisorLog(`WORKER STDERR: ${data.toString().trim()}`);
        });
        
        pythonProcess.on('close', (code, signal) => {
            supervisorLog(`Worker process exited. Code: ${code}, Signal: ${signal}. Supervisor will exit.`);
            process.exit(code === null ? 1 : code);
        });

        pythonProcess.on('error', (err) => {
            supervisorLog(`Failed to start worker process. Error: ${err.message}`);
            process.exit(1);
        });

        supervisorLog('Worker process event listeners are attached.');
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