#!/usr/bin/env node

const os = require('os');
const fs = require('fs');
const path = require('path');
const { initialize } = require('../index.js');
const { version } = require('../package.json');

// --- Logger Setup ---
// We create a persistent log file to capture the entire lifecycle.
const logFilePath = path.join(os.homedir(), `.remote-terminal-mcp-v${version}-debug.log`);
const logStream = fs.createWriteStream(logFilePath, { flags: 'w' });

const log = (message) => {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] [cli] ${message}\n`;
    logStream.write(logMessage);
    // Also write to stderr so it can be seen in Cursor's MCP Logs if it gets that far.
    process.stderr.write(logMessage);
};
// --- End Logger Setup ---

log(`CLI script started. Version: ${version}, Node.js: ${process.version}.`);
log(`Full log file at: ${logFilePath}`);

// Graceful exit handling
const cleanup = (signal) => {
    log(`Received ${signal}. Cleaning up and exiting.`);
    logStream.end(() => process.exit());
};
process.on('SIGINT', () => cleanup('SIGINT'));
process.on('SIGTERM', () => cleanup('SIGTERM'));

// Main execution block
try {
    log('Attempting to initialize the service...');
    // The 'initialize' function contains the core logic (starting the python worker)
    // and will keep the process alive. We pass it our log function.
    initialize(log);
    log('Service initialization sequence started successfully.');
} catch (error) {
    log(`FATAL: An uncaught error occurred during initialization: ${error.message}`);
    log(error.stack);
    process.exit(1);
}

// This is a temporary diagnostic measure to prevent the event loop from exiting
// prematurely, allowing us to see all asynchronous logs.
setInterval(() => {
    log('Process kept alive by diagnostic interval.');
}, 1000 * 60 * 5); // Log every 5 minutes 