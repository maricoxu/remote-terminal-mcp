#!/usr/bin/env node

/**
 * Debug MCP Server - Pure Node.js Implementation
 * 用于调试 MCP 协议问题
 */

const readline = require('readline');

class DebugMCPServer {
    constructor() {
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout,
            terminal: false
        });
        
        this.setupHandlers();
        this.log('Debug MCP Server starting...');
    }

    log(message) {
        console.error(`[DEBUG MCP] ${new Date().toISOString()} ${message}`);
    }

    setupHandlers() {
        this.rl.on('line', (line) => {
            try {
                this.log(`Received: ${line}`);
                const message = JSON.parse(line);
                this.handleMessage(message);
            } catch (error) {
                this.log(`Error parsing message: ${error.message}`);
                this.log(`Raw line: ${line}`);
            }
        });

        this.rl.on('close', () => {
            this.log('Input stream closed');
            process.exit(0);
        });

        process.on('SIGINT', () => {
            this.log('Received SIGINT, shutting down...');
            process.exit(0);
        });
    }

    handleMessage(message) {
        this.log(`Handling message: ${JSON.stringify(message)}`);

        switch (message.method) {
            case 'initialize':
                this.handleInitialize(message);
                break;
            case 'tools/list':
                this.handleToolsList(message);
                break;
            default:
                this.log(`Unknown method: ${message.method}`);
                this.sendError(message.id, -32601, 'Method not found');
        }
    }

    handleInitialize(message) {
        this.log('Handling initialize request');
        
        const response = {
            jsonrpc: '2.0',
            id: message.id,
            result: {
                protocolVersion: '2024-11-05',
                capabilities: {
                    tools: {},
                    resources: {},
                    prompts: {},
                    logging: {}
                },
                serverInfo: {
                    name: 'remote-terminal-mcp-debug',
                    version: '0.1.0'
                }
            }
        };

        this.sendResponse(response);
    }

    handleToolsList(message) {
        this.log('Handling tools/list request');
        
        const response = {
            jsonrpc: '2.0',
            id: message.id,
            result: {
                tools: [
                    {
                        name: 'debug_test',
                        description: 'A debug test tool',
                        inputSchema: {
                            type: 'object',
                            properties: {
                                message: {
                                    type: 'string',
                                    description: 'Test message'
                                }
                            }
                        }
                    }
                ]
            }
        };

        this.sendResponse(response);
    }

    sendResponse(response) {
        const responseStr = JSON.stringify(response);
        this.log(`Sending response: ${responseStr}`);
        console.log(responseStr);
    }

    sendError(id, code, message) {
        const error = {
            jsonrpc: '2.0',
            id: id,
            error: {
                code: code,
                message: message
            }
        };
        
        const errorStr = JSON.stringify(error);
        this.log(`Sending error: ${errorStr}`);
        console.log(errorStr);
    }
}

// 启动调试服务器
if (require.main === module) {
    new DebugMCPServer();
}

module.exports = DebugMCPServer; 