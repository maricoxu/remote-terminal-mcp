#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// This script is executed after the package is installed.
// Its purpose is to programmatically ensure that our CLI entry point
// has the necessary execute permissions. This is a robust way to
// solve "Permission denied" errors that can occur when npm/npx
// fail to properly set the executable bit during installation.

const cliScriptPath = path.join(__dirname, '..', 'bin', 'cli.js');

try {
  // Set permissions to rwxr-xr-x (755)
  fs.chmodSync(cliScriptPath, 0o755);
  // We don't log on success to keep installation clean,
  // but you could add a console.log here for debugging.
} catch (error) {
  // If we fail, log the error clearly. This is critical for debugging.
  console.error(
    `[postinstall.js] FATAL: Failed to set execute permission on ${cliScriptPath}`
  );
  console.error(error);
  // Exit with a non-zero code to indicate failure.
  process.exit(1);
} 