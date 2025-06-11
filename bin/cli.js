#!/usr/bin/env node

const os = require('os');
const fs = require('fs');
const path = require('path');
const { initialize } = require('../index.js');
const { version } = require('../package.json'); // More robust way to get version

// This is the main entry point for the CLI.
// We are setting up a dedicated log file to capture everything that happens
// from the moment this script starts.

const logFilePath = path.join(os.homedir(), `remote-terminal-mcp-v${version}-debug.log`);
const logStream = fs.createWriteStream(logFilePath, { flags: 'w' }); // 'w' to overwrite on start

const log = (message) => {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] [cli] ${message}\n`;
    logStream.write(logMessage); // Write to the dedicated log file
    process.stderr.write(logMessage); // Also write to stderr for real-time viewing in debug context
};

log(`CLI script started. Node.js version: ${process.version}.`);
log(`Package version: ${version}.`);
log(`Log file path: ${logFilePath}.`);
log(`CWD: ${process.cwd()}.`);
log(`ENV: ${JSON.stringify(process.env, null, 2)}.`);
log('Initializing supervisor...');

try {
    initialize(logStream);
    log('Supervisor initialization sequence started.');
} catch (error) {
    log(`FATAL: An uncaught error occurred: ${error.message}`);
    log(error.stack);
    process.exit(1);
}

// This is a temporary diagnostic measure to prevent the event loop from exiting
// prematurely, allowing us to see all asynchronous logs.
setInterval(() => {
    log('Process kept alive by diagnostic interval.');
}, 1000 * 60 * 5); // Log every 5 minutes 