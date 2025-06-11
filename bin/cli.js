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

const log = (message) => {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] [cli] ${message}\n`;
    logStream.write(logMessage); // Write to the dedicated log file
    process.stderr.write(logMessage); // Also write to stderr for real-time viewing in debug context
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