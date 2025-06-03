#!/usr/bin/env node

/**
 * Remote Terminal MCP - Ultra Minimal Version
 * 
 * @author xuyehua
 * @version 0.1.0
 */

const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const chalk = require('chalk');

class RemoteTerminalMCP {
    constructor() {
        this.packageDir = __dirname;
        this.pythonDir = path.join(this.packageDir, 'python');
        this.args = this.parseArgs();
    }

    parseArgs() {
        const args = process.argv.slice(2);
        return {
            isTestMode: args.includes('--test') || args.includes('-t'),
            isDebugMode: args.includes('--debug') || args.includes('-d'),
            isHelpMode: args.includes('--help') || args.includes('-h'),
        };
    }

    async main() {
        try {
            if (this.args.isHelpMode) {
                this.showHelp();
                return;
            }

            if (this.args.isTestMode) {
                await this.runTests();
                return;
            }

            await this.startMCPServer();
            
        } catch (error) {
            console.error(chalk.red('🚨 Error:'), error.message);
            process.exit(1);
        }
    }

    showHelp() {
        console.log(chalk.cyan(`
🖥️  Remote Terminal MCP - Ultra Minimal Version

Usage:
  npx @xuyehua/remote-terminal-mcp [options]

Options:
  -h, --help      Show help
  -t, --test      Run tests  
  -d, --debug     Debug mode

Examples:
  # Start MCP server
  npx @xuyehua/remote-terminal-mcp
  
  # Run tests
  npx @xuyehua/remote-terminal-mcp --test
`));
    }

    async startMCPServer() {
        const pythonScript = path.join(this.pythonDir, 'mcp_server.py');
        
        if (!fs.existsSync(pythonScript)) {
            console.error(chalk.red(`Python script not found: ${pythonScript}`));
            process.exit(1);
        }

        if (this.args.isDebugMode) {
            console.error(chalk.blue('🚀 Starting MCP Server...'));
            console.error(chalk.gray(`Python script: ${pythonScript}`));
        }

        // 启动Python MCP服务器
        const mcp = spawn('python3', [pythonScript], {
            stdio: ['pipe', 'pipe', this.args.isDebugMode ? 'inherit' : 'pipe']
        });

        // 转发stdio用于MCP通信
        process.stdin.pipe(mcp.stdin);
        mcp.stdout.pipe(process.stdout);

        // 处理进程事件
        mcp.on('close', (code) => {
            if (this.args.isDebugMode) {
                console.error(chalk.yellow(`MCP server exited with code: ${code}`));
            }
            process.exit(code);
        });

        mcp.on('error', (error) => {
            console.error(chalk.red('MCP server error:'), error.message);
            process.exit(1);
        });

        // 优雅退出处理
        process.on('SIGINT', () => {
            if (this.args.isDebugMode) {
                console.error(chalk.yellow('\\nShutting down MCP server...'));
            }
            mcp.kill('SIGTERM');
        });
    }

    async runTests() {
        console.log(chalk.blue('🧪 Running tests...\\n'));

        const tests = [
            { name: 'Python script', test: () => this.testPythonScript() },
            { name: 'MCP protocol', test: () => this.testMCPProtocol() }
        ];

        let passedTests = 0;
        
        for (const { name, test } of tests) {
            try {
                const result = await test();
                if (result) {
                    console.log(chalk.green(`✔ ${name} test passed`));
                    passedTests++;
                } else {
                    console.log(chalk.red(`✖ ${name} test failed`));
                }
            } catch (error) {
                console.log(chalk.red(`✖ ${name} test error: ${error.message}`));
            }
        }

        console.log('');
        if (passedTests === tests.length) {
            console.log(chalk.green('🎉 All tests passed!'));
            console.log(chalk.blue('\\n💡 Usage:'));
            console.log('Add to ~/.cursor/mcp.json:');
            console.log(chalk.gray(JSON.stringify({
                "remote-terminal": {
                    "command": "npx",
                    "args": ["-y", "@xuyehua/remote-terminal-mcp"],
                    "disabled": false
                }
            }, null, 2)));
        } else {
            console.log(chalk.red(`❌ ${tests.length - passedTests}/${tests.length} tests failed`));
            process.exit(1);
        }

        process.exit(0);
    }

    async testPythonScript() {
        const pythonScript = path.join(this.pythonDir, 'mcp_server.py');
        
        if (!fs.existsSync(pythonScript)) {
            throw new Error('Python script does not exist');
        }

        // Test script syntax
        return new Promise((resolve) => {
            const process = spawn('python3', ['-m', 'py_compile', pythonScript], {
                stdio: 'pipe'
            });
            
            process.on('close', (code) => {
                resolve(code === 0);
            });
        });
    }

    async testMCPProtocol() {
        const pythonScript = path.join(this.pythonDir, 'mcp_server.py');
        
        if (!fs.existsSync(pythonScript)) {
            return false;
        }

        const content = fs.readFileSync(pythonScript, 'utf8');
        const requiredElements = ['handle_request', 'initialize', 'tools/list'];
        
        return requiredElements.every(element => content.includes(element));
    }
}

// 直接执行
if (require.main === module) {
    const terminal = new RemoteTerminalMCP();
    terminal.main().catch(error => {
        console.error(chalk.red('🚨 Unhandled error:'), error);
        process.exit(1);
    });
}

module.exports = RemoteTerminalMCP;