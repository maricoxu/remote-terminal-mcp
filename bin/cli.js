#!/usr/bin/env node

const path = require('path');
const { spawn } = require('child_process');

/**
 * This script is a long-lived supervisor.
 * Its job is to spawn the actual server process (index.js) and then wait,
 * keeping itself alive as long as the server is running.
 * This is the process that Cursor monitors.
 */
function main() {
    const packageRoot = path.resolve(__dirname, '..');
    const serverScript = path.join(packageRoot, 'index.js');

    // Spawn the server script as a child process.
    // It is NOT detached. The parent (this script) will live as long as the child.
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
        process.exit(code === null ? 1 : code);
    });

    // Handle errors during the spawn itself (e.g., 'node' not found).
    child.on('error', (err) => {
        console.error(`[MCP Supervisor] Failed to start server process: ${err.message}`);
        process.exit(1);
    });

    // Ensure that if the supervisor is killed, it also kills the child.
    const onSignal = (signal) => {
        child.kill(signal);
    };
    process.on('SIGINT', () => onSignal('SIGINT'));
    process.on('SIGTERM', () => onSignal('SIGTERM'));
}

// Execute the main function.
try {
    main();
} catch (error) {
    console.error(`[MCP Supervisor] Catastrophic error: ${error.message}`);
    process.exit(1);
} 