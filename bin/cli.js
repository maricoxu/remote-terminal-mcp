#!/usr/bin/env node

const os = require('os');
const fs = require('fs');
const path = require('path');
const { initialize } = require('../index.js');

// This is the main entry point for the CLI.
// We are setting up a dedicated log file to capture everything that happens
// from the moment this script starts.

const logFilePath = path.join(os.homedir(), `remote-terminal-mcp-v${process.env.npm_package_version}-debug.log`);
const logStream = fs.createWriteStream(logFilePath, { flags: 'w' }); // 'w' to overwrite on start

// The process's stdout is connected to the parent (Cursor).
// We pipe our log stream to stderr so we can see logs in debug mode if needed,
// but they won't interfere with the MCP communication over stdout.
logStream.pipe(process.stderr);

const log = (message) => {
    const timestamp = new Date().toISOString();
    logStream.write(`[${timestamp}] [cli] ${message}\n`);
};

log(`CLI script started. Node.js version: ${process.version}`);
log(`Log file path: ${logFilePath}`);
log(`Package version from env: ${process.env.npm_package_version}`);
log(`Current working directory: ${process.cwd()}`);
log('Initializing supervisor...');

try {
    initialize(logStream);
    log('Supervisor initialized successfully.');
} catch (error) {
    log(`FATAL: An uncaught error occurred during initialization: ${error.message}`);
    log(error.stack);
    process.exit(1);
} 