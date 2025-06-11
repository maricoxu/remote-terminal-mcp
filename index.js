#!/usr/bin/env node

/**
 * Remote Terminal MCP - Ultra Minimal Version
 * 
 * @author xuyehua
 * @version 0.1.0
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');

// --- Worker Logger ---
const logFile = path.join(os.homedir(), 'mcp_service_debug.log');
// Subsequent loggers should only append to the file.
const log = (msg) => {
    try {
        fs.appendFileSync(logFile, `[WORKER] [${new Date().toISOString()}] ${msg}\n`);
    } catch (e) {
        // If logging fails, there's not much we can do, but we shouldn't crash.
    }
};
log("Worker starting.");
// --- End Logger ---

class RemoteTerminalMCP {
    constructor() {
        this.packageDir = __dirname;
        this.pythonDir = path.join(this.packageDir, 'python');
        this.args = this.parseArgs();
        log('Constructor finished.');
    }

    parseArgs() {
        log('Parsing arguments...');
        const args = process.argv.slice(2);
        log(`Arguments found: ${args.join(', ')}`);
        return {
            isDebugMode: args.includes('--debug') || args.includes('-d'),
            isHelpMode: args.includes('--help') || args.includes('-h'),
        };
    }

    async main() {
        log('Main function started.');
        if (this.args.isHelpMode) {
            this.showHelp();
            return;
        }
        
        await this.startMCPServer();
        log('Main function finished.');
    }

    showHelp() {
        console.log(`
Remote Terminal MCP - Ultra Minimal Version

Usage:
  npx @xuyehua/remote-terminal-mcp [options]

Options:
  -h, --help      Show help 
  -d, --debug     Debug mode

This command starts the MCP server directly.
        `);
    }

    async startMCPServer() {
        log('Attempting to start MCP server (Python process)...');
        const pythonScript = path.join(this.pythonDir, 'mcp_server.py');
        
        log(`Checking for python script at: ${pythonScript}`);
        if (!fs.existsSync(pythonScript)) {
            const errorMsg = 'Python script not found, exiting.';
            log(`ERROR: ${errorMsg}`);
            console.error(errorMsg);
            process.exit(1);
        }

        const env = { ...process.env };
        if (this.args.isDebugMode || process.env.MCP_DEBUG) {
            env.MCP_DEBUG = '1';
        }
        
        // The command to execute. Using `python3` relies on it being in the shell's PATH.
        const command = `python3 "${pythonScript}"`;
        log(`Spawning command within a shell: ${command}`);
        const mcp = spawn(command, {
            shell: true, // IMPORTANT: Lets the user's shell find python3 via its PATH.
            stdio: ['pipe', 'pipe', 'pipe'], // Capture stdin, stdout, and stderr.
            env: { ...process.env, ...env }, // Pass through parent env and add our own.
        });
        log('Python process spawned.');

        mcp.stderr.on('data', (data) => {
            const message = data.toString();
            log(`[CRITICAL] Python stderr: ${message}`);
            if (this.args.isDebugMode) {
                console.error(`[Python stderr] ${message}`);
            }
        });

        process.stdin.pipe(mcp.stdin);
        mcp.stdout.pipe(process.stdout);

        mcp.on('close', (code, signal) => {
            log(`Python process exited. Code: ${code}, Signal: ${signal}. Worker process will now exit.`);
            if (this.args.isDebugMode) {
                console.error(`MCP server exited. Code: ${code}, Signal: ${signal}`);
            }
            process.exit(code || 1);
        });

        mcp.on('error', (error) => {
            log(`[CRITICAL] Python process spawn ERROR: ${error.message}. Worker process will now exit.`);
            if (this.args.isDebugMode) {
                console.error('MCP server error:', error.message);
            }
            process.exit(1);
        });

        process.on('SIGINT', () => {
            log('Received SIGINT. Shutting down python process...');
            if (this.args.isDebugMode) {
                console.error('Shutting down MCP server...');
            }
            mcp.kill('SIGTERM');
        });
        log('Event listeners for python process are set up.');
    }
}

module.exports = RemoteTerminalMCP;

if (require.main === module) {
    log('Script is main module, creating instance and running main().');
    const terminal = new RemoteTerminalMCP();
    terminal.main().catch(error => {
        log(`Unhandled error in main execution: ${error.message}. Stack: ${error.stack}`);
        console.error(`Unhandled error in main execution: ${error.message}`);
        console.error(error.stack);
        process.exit(1);
    });
}