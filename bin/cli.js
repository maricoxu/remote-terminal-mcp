#!/usr/bin/env node

const path = require('path');
const { initialize } = require('../index.js');

// A simple logger that outputs to stderr, which can be seen in Cursor's MCP logs.
const log = (message) => {
    // We check for a specific environment variable to enable debug logging.
    // This makes the service quiet by default in production.
    if (process.env.MCP_DEBUG === '1') {
        const timestamp = new Date().toISOString();
        process.stderr.write(`[${timestamp}] [cli] ${message}\n`);
    }
};

// Main execution block
try {
    log('CLI entrypoint reached. Initializing service...');
    initialize(log);
    log('Service initialization sequence started.');
} catch (error) {
    const errorLog = (msg) => process.stderr.write(`[${new Date().toISOString()}] [cli] [FATAL] ${msg}\n`);
    errorLog(`An uncaught error occurred during initialization: ${error.message}`);
    errorLog(error.stack);
    process.exit(1);
} 