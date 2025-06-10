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

class RemoteTerminalMCP {
    constructor() {
        this.packageDir = __dirname;
        this.pythonDir = path.join(this.packageDir, 'python');
        this.args = this.parseArgs();
    }

    parseArgs() {
        const args = process.argv.slice(2);
        return {
            isDebugMode: args.includes('--debug') || args.includes('-d'),
            isHelpMode: args.includes('--help') || args.includes('-h'),
        };
    }

    async main() {
        if (this.args.isHelpMode) {
            this.showHelp();
            return;
        }
        
        await this.startMCPServer();
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
        const pythonScript = path.join(this.pythonDir, 'mcp_server.py');
        
        if (!fs.existsSync(pythonScript)) {
            const errorMsg = 'Python script not found, exiting.';
            console.error(errorMsg);
            process.exit(1);
        }

        const env = { ...process.env };
        if (this.args.isDebugMode || process.env.MCP_DEBUG) {
            env.MCP_DEBUG = '1';
        }
        
        const mcp = spawn('python3', [pythonScript], {
            stdio: ['pipe', 'pipe', 'pipe'],
            env: env
        });

        mcp.stderr.on('data', (data) => {
            const message = data.toString().trim();
            if (this.args.isDebugMode) {
                console.error(`[Python stderr] ${message}`);
            }
        });

        process.stdin.pipe(mcp.stdin);
        mcp.stdout.pipe(process.stdout);

        mcp.on('close', (code) => {
            if (this.args.isDebugMode) {
                console.error(`MCP server exited with code: ${code}`);
            }
            process.exit(code || 0);
        });

        mcp.on('error', (error) => {
            if (this.args.isDebugMode) {
                console.error('MCP server error:', error.message);
            }
            process.exit(1);
        });

        process.on('SIGINT', () => {
            if (this.args.isDebugMode) {
                console.error('Shutting down MCP server...');
            }
            mcp.kill('SIGTERM');
        });
    }
}

module.exports = RemoteTerminalMCP;

if (require.main === module) {
    const terminal = new RemoteTerminalMCP();
    terminal.main().catch(error => {
        console.error(`Unhandled error in main execution: ${error.message}`);
        console.error(error.stack);
        process.exit(1);
    });
}