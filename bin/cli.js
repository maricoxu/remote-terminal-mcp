#!/usr/bin/env node

const path = require('path');
const { spawn } = require('child_process');

/**
 * This is the main entry point for the MCP service when called by npx.
 * Its only job is to spawn the actual server process (index.js)
 * and then exit, handing over control.
 */
function main() {
    // Determine the path to the actual server script.
    // __dirname is the directory of the currently executing script (bin/cli.js),
    // so we go up one level to the package root.
    const packageRoot = path.resolve(__dirname, '..');
    const serverScript = path.join(packageRoot, 'index.js');

    // Spawn the server script as a detached, independent process.
    // This is crucial for it to run as a long-lived service.
    const child = spawn('node', [serverScript], {
        detached: true, // Allows the child to run independently of the parent.
        stdio: 'pipe', // We will pipe stdin/stdout/stderr
    });

    // Pipe the parent's stdio to the child, so Cursor can communicate with it.
    process.stdin.pipe(child.stdin);
    child.stdout.pipe(process.stdout);
    child.stderr.pipe(process.stderr);

    // The child process should not keep the parent alive.
    child.unref();

    // The CLI script has done its job, so it can now exit.
    // The child process will continue to run in the background.
    process.exit(0);
}

// Execute the main function.
try {
    main();
} catch (error) {
    // If there's a catastrophic error during spawn, log it and exit.
    console.error(`Failed to launch MCP server: ${error.message}`);
    process.exit(1);
} 