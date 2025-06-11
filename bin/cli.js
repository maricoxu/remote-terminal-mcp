#!/usr/bin/env node

const path = require('path');
const os = require('os');
const fs = require('fs');
const { spawn } = require('child_process');

// --- Supervisor Logger (v0.4.17) ---
const logFile = path.join(os.homedir(), 'supervisor-v0.4.17-debug.log');
fs.writeFileSync(logFile, `[SUPERVISOR] [${new Date().toISOString()}] Supervisor starting.\n`);
const log = (msg) => fs.appendFileSync(logFile, `[SUPERVISOR] [${new Date().toISOString()}] ${msg}\n`);
log(`Received Environment Variables:\n${JSON.stringify(process.env, null, 2)}`);
// --- End Logger ---

function main() {
    log('Main function started.');
    const packageRoot = path.resolve(__dirname, '..');
    const serverScript = path.join(packageRoot, 'index.js');
    log(`Resolved server script path: ${serverScript}`);

    log('Spawning child process (index.js)...');
    const child = spawn('node', [serverScript], {
        stdio: ['pipe', 'pipe', 'pipe', 'ipc'], // Inherit stdio and add ipc channel
        env: process.env, // Pass through the full environment
    });

    child.on('close', (code, signal) => {
        log(`Child process closed. Code: ${code}, Signal: ${signal}. Supervisor exiting.`);
        process.exit(code === null ? 1 : code);
    });

    child.on('error', (err) => {
        log(`[CRITICAL] Failed to start server process: ${err.message}. Supervisor exiting.`);
        process.exit(1);
    });
    
    // Relay stdout/stderr from child to this process's log file for unified debugging
    child.stdout.on('data', (data) => log(`[CHILD STDOUT] ${data.toString().trim()}`));
    child.stderr.on('data', (data) => log(`[CHILD STDERR] ${data.toString().trim()}`));

    const onSignal = (signal) => {
        child.kill(signal);
    };
    process.on('SIGINT', () => onSignal('SIGINT'));
    process.on('SIGTERM', () => onSignal('SIGTERM'));
    
    log('Supervisor setup complete. Waiting for child process to exit.');
}

try {
    main();
} catch (error) {
    log(`[CRITICAL] Catastrophic error in supervisor: ${error.message}. Supervisor exiting.`);
    process.exit(1);
} 