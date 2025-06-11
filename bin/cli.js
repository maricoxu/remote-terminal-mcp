#!/usr/bin/env node

const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

// --- Supervisor Logger ---
const logFile = '/tmp/supervisor-debug.log';
fs.writeFileSync(logFile, `[${new Date().toISOString()}] Supervisor starting.\n`);
const log = (msg) => fs.appendFileSync(logFile, `[${new Date().toISOString()}] ${msg}\n`);
// --- End Logger ---

/**
 * This script is a long-lived supervisor.
 * Its job is to spawn the actual server process (index.js) and then wait,
 * keeping itself alive as long as the server is running.
 * This is the process that Cursor monitors.
 */
function main() {
    log('Main function started.');
    const packageRoot = path.resolve(__dirname, '..');
    const serverScript = path.join(packageRoot, 'index.js');
    log(`Resolved server script path: ${serverScript}`);

    // Spawn the server script as a child process.
    // It is NOT detached. The parent (this script) will live as long as the child.
    log('Spawning child process...');
    const child = spawn('node', [serverScript], {
        // Use 'inherit' to directly pass through the stdio streams from this
        // process to the child process. This is the simplest and most robust way
        // for Cursor to communicate with our actual server.
        stdio: 'inherit',
    });

    // When the child process (the server) exits, this supervisor process
    // should also exit with the same code. This correctly signals the
    // service status back to Cursor.
    child.on('close', (code) => {
        log(`Child process closed with code: ${code}. Supervisor exiting.`);
        process.exit(code === null ? 1 : code);
    });

    // Handle errors during the spawn itself (e.g., 'node' not found).
    child.on('error', (err) => {
        log(`Failed to start server process: ${err.message}. Supervisor exiting.`);
        console.error(`[MCP Supervisor] Failed to start server process: ${err.message}`);
        process.exit(1);
    });

    // Ensure that if the supervisor is killed, it also kills the child.
    const onSignal = (signal) => {
        child.kill(signal);
    };
    process.on('SIGINT', () => onSignal('SIGINT'));
    process.on('SIGTERM', () => onSignal('SIGTERM'));
    
    log('Supervisor setup complete. Waiting for child process to exit.');
}

// Execute the main function.
try {
    main();
} catch (error) {
    log(`Catastrophic error in supervisor: ${error.message}. Supervisor exiting.`);
    console.error(`[MCP Supervisor] Catastrophic error: ${error.message}`);
    process.exit(1);
} 