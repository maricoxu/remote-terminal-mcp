#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// This script runs after the package is installed.
// Its purpose is to ensure the main CLI script is executable,
// which is the root cause of the "Permission denied" error.

const cliScriptPath = path.resolve(__dirname, '..', 'bin', 'cli.js');

try {
    // Set permission to rwxr-xr-x (755)
    fs.chmodSync(cliScriptPath, '755');
    // We can't rely on file logging, but a console log might appear in install logs.
    console.log(`[postinstall] Successfully set executable permission on ${cliScriptPath}`);
} catch (err) {
    console.error(`[postinstall] Failed to set executable permission on ${cliScriptPath}:`, err);
    // If this fails, the install will likely still succeed, but the error
    // will be logged, and the "Permission denied" issue will persist.
} 