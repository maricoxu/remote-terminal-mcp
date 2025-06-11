#!/usr/bin/env node

/**
 * Remote Terminal MCP - Ultra Minimal Version
 * 
 * @author xuyehua
 * @version 0.1.0
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

// --- Worker Logger ---
const logFile = path.join(process.cwd(), 'worker-debug.log');
fs.writeFileSync(logFile, `[${new Date().toISOString()}] Worker starting.\n`);
const log = (msg) => fs.appendFileSync(logFile, `[${new Date().toISOString()}] ${msg}\n`);
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
        
        log('Spawning python3 process...');
        const mcp = spawn('python3', [pythonScript], {
            stdio: ['pipe', 'pipe', 'pipe'],
            env: env
        });
        log('Python process spawned.');

        mcp.stderr.on('data', (data) => {
            const message = data.toString();
            log(`[Python stderr] ${message}`);
            if (this.args.isDebugMode) {
                console.error(`[Python stderr] ${message}`);
            }
        });

        process.stdin.pipe(mcp.stdin);
        mcp.stdout.pipe(process.stdout);

        mcp.on('close', (code) => {
            log(`Python process exited with code: ${code}. Node worker process will now exit.`);
            if (this.args.isDebugMode) {
                console.error(`MCP server exited with code: ${code}`);
            }
            process.exit(code || 0);
        });

        mcp.on('error', (error) => {
            log(`Python process spawn error: ${error.message}. Node worker process will now exit.`);
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