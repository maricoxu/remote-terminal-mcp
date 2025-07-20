#!/usr/bin/env node

/**
 * Remote Terminal MCP Server - Pure Node.js Implementation
 * 完整的远程终端 MCP 服务器
 */

const readline = require('readline');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawn } = require('child_process');

class RemoteTerminalMCPServer {
    constructor() {
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout,
            terminal: false
        });
        
        this.configDir = path.join(os.homedir(), '.remote-terminal');
        this.configFile = path.join(this.configDir, 'config.yaml');
        
        this.setupHandlers();
        this.log('Remote Terminal MCP Server starting...');
        this.ensureConfigDir();
    }

    log(message) {
        console.error(`[RT-MCP] ${new Date().toISOString()} ${message}`);
    }

    ensureConfigDir() {
        if (!fs.existsSync(this.configDir)) {
            fs.mkdirSync(this.configDir, { recursive: true });
            this.log(`Created config directory: ${this.configDir}`);
        }
    }

    setupHandlers() {
        this.rl.on('line', (line) => {
            try {
                const message = JSON.parse(line);
                this.handleMessage(message);
            } catch (error) {
                this.log(`Error parsing message: ${error.message}`);
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
        switch (message.method) {
            case 'initialize':
                this.handleInitialize(message);
                break;
            case 'tools/list':
                this.handleToolsList(message);
                break;
            case 'tools/call':
                this.handleToolCall(message);
                break;
            default:
                this.sendError(message.id, -32601, 'Method not found');
        }
    }

    handleInitialize(message) {
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
                    name: 'remote-terminal-mcp',
                    version: '0.13.3'
                }
            }
        };

        this.sendResponse(response);
    }

    handleToolsList(message) {
        const tools = [
            {
                name: 'list_servers',
                description: 'List all configured remote servers',
                inputSchema: {
                    type: 'object',
                    properties: {}
                }
            },
            {
                name: 'interactive_config_wizard',
                description: 'Launch interactive configuration wizard to set up a new server',
                inputSchema: {
                    type: 'object',
                    properties: {
                        server_type: {
                            type: 'string',
                            enum: ['ssh', 'relay', 'docker', 'custom'],
                            description: 'Type of server to configure'
                        },
                        quick_mode: {
                            type: 'boolean',
                            default: true,
                            description: 'Use quick configuration mode'
                        }
                    }
                }
            },
            {
                name: 'create_server_config',
                description: 'Create a new server configuration',
                inputSchema: {
                    type: 'object',
                    properties: {
                        name: {
                            type: 'string',
                            description: 'Server name (unique identifier)'
                        },
                        host: {
                            type: 'string',
                            description: 'Server hostname or IP address'
                        },
                        username: {
                            type: 'string',
                            description: 'Username for SSH connection'
                        },
                        port: {
                            type: 'integer',
                            default: 22,
                            description: 'SSH port'
                        },
                        description: {
                            type: 'string',
                            description: 'Server description'
                        }
                    },
                    required: ['name', 'host', 'username']
                }
            },
            {
                name: 'connect_server',
                description: 'Connect to a remote server',
                inputSchema: {
                    type: 'object',
                    properties: {
                        server_name: {
                            type: 'string',
                            description: 'Name of the server to connect to'
                        }
                    },
                    required: ['server_name']
                }
            },
            {
                name: 'execute_command',
                description: 'Execute a command on a server',
                inputSchema: {
                    type: 'object',
                    properties: {
                        command: {
                            type: 'string',
                            description: 'Command to execute'
                        },
                        server: {
                            type: 'string',
                            description: 'Server name (optional, uses default if not specified)'
                        }
                    },
                    required: ['command']
                }
            }
        ];

        const response = {
            jsonrpc: '2.0',
            id: message.id,
            result: { tools }
        };

        this.sendResponse(response);
    }

    async handleToolCall(message) {
        const { name, arguments: args } = message.params;
        
        try {
            let result;
            
            switch (name) {
                case 'list_servers':
                    result = await this.listServers();
                    break;
                case 'interactive_config_wizard':
                    result = await this.interactiveConfigWizard(args);
                    break;
                case 'create_server_config':
                    result = await this.createServerConfig(args);
                    break;
                case 'connect_server':
                    result = await this.connectServer(args);
                    break;
                case 'execute_command':
                    result = await this.executeCommand(args);
                    break;
                default:
                    throw new Error(`Unknown tool: ${name}`);
            }

            this.sendResponse({
                jsonrpc: '2.0',
                id: message.id,
                result: {
                    content: [
                        {
                            type: 'text',
                            text: result
                        }
                    ]
                }
            });
        } catch (error) {
            this.sendError(message.id, -32000, error.message);
        }
    }

    async listServers() {
        if (!fs.existsSync(this.configFile)) {
            return 'No servers configured yet. Use the interactive_config_wizard to set up your first server.';
        }

        try {
            const configContent = fs.readFileSync(this.configFile, 'utf8');
            // 简单的 YAML 解析（实际项目中应该使用专门的 YAML 库）
            const servers = this.parseSimpleYaml(configContent);
            
            if (Object.keys(servers).length === 0) {
                return 'No servers configured yet.';
            }

            let result = 'Configured servers:\n\n';
            for (const [name, config] of Object.entries(servers)) {
                result += `📡 ${name}\n`;
                result += `   Host: ${config.host || 'N/A'}\n`;
                result += `   User: ${config.username || 'N/A'}\n`;
                result += `   Port: ${config.port || 22}\n`;
                if (config.description) {
                    result += `   Description: ${config.description}\n`;
                }
                result += '\n';
            }

            return result;
        } catch (error) {
            return `Error reading server configurations: ${error.message}`;
        }
    }

    async interactiveConfigWizard(args) {
        const serverType = args.server_type || 'ssh';
        const quickMode = args.quick_mode !== false;

        return `🚀 Interactive Configuration Wizard
        
Server Type: ${serverType}
Quick Mode: ${quickMode ? 'Enabled' : 'Disabled'}

This is a Node.js implementation of the configuration wizard.
In a full implementation, this would guide you through:

1. Server connection details (host, username, port)
2. Authentication method (SSH key, password)
3. Optional Docker configuration
4. Connection testing
5. Saving the configuration

For now, please use the create_server_config tool to manually create a server configuration.

Example:
- Name: my-server
- Host: example.com
- Username: myuser
- Port: 22`;
    }

    async createServerConfig(args) {
        const { name, host, username, port = 22, description } = args;

        if (!name || !host || !username) {
            throw new Error('Missing required parameters: name, host, username');
        }

        // 创建服务器配置
        const serverConfig = {
            [name]: {
                host,
                username,
                port,
                description: description || `Server ${name}`,
                connection_type: 'ssh',
                created_at: new Date().toISOString()
            }
        };

        // 读取现有配置
        let existingConfig = {};
        if (fs.existsSync(this.configFile)) {
            try {
                const content = fs.readFileSync(this.configFile, 'utf8');
                existingConfig = this.parseSimpleYaml(content);
            } catch (error) {
                this.log(`Warning: Could not parse existing config: ${error.message}`);
            }
        }

        // 合并配置
        const newConfig = { ...existingConfig, ...serverConfig };

        // 保存配置
        const yamlContent = this.generateSimpleYaml(newConfig);
        fs.writeFileSync(this.configFile, yamlContent, 'utf8');

        return `✅ Server configuration created successfully!

Server: ${name}
Host: ${host}
Username: ${username}
Port: ${port}
${description ? `Description: ${description}` : ''}

Configuration saved to: ${this.configFile}

You can now use connect_server to connect to this server.`;
    }

    async connectServer(args) {
        const { server_name } = args;

        if (!server_name) {
            throw new Error('Server name is required');
        }

        // 这里应该实现实际的连接逻辑
        return `🔌 Connecting to server: ${server_name}

Note: This is a Node.js implementation demo.
In a full implementation, this would:

1. Read server configuration from ${this.configFile}
2. Establish SSH connection
3. Set up terminal session
4. Return connection status

For now, this is a placeholder response.`;
    }

    async executeCommand(args) {
        const { command, server } = args;

        if (!command) {
            throw new Error('Command is required');
        }

        // 这里应该实现实际的命令执行逻辑
        return `💻 Executing command: ${command}
${server ? `On server: ${server}` : 'On default server'}

Note: This is a Node.js implementation demo.
In a full implementation, this would:

1. Connect to the specified server (or default)
2. Execute the command remotely
3. Return the command output
4. Handle errors and timeouts

For now, this is a placeholder response.`;
    }

    // 简单的 YAML 解析器（仅用于演示）
    parseSimpleYaml(content) {
        const result = {};
        const lines = content.split('\n');
        let currentServer = null;

        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#')) continue;

            if (!trimmed.startsWith(' ') && trimmed.endsWith(':')) {
                currentServer = trimmed.slice(0, -1);
                result[currentServer] = {};
            } else if (currentServer && trimmed.includes(':')) {
                const [key, ...valueParts] = trimmed.split(':');
                const value = valueParts.join(':').trim();
                result[currentServer][key.trim()] = value;
            }
        }

        return result;
    }

    // 简单的 YAML 生成器（仅用于演示）
    generateSimpleYaml(config) {
        let yaml = '# Remote Terminal MCP Configuration\n';
        yaml += `# Generated at: ${new Date().toISOString()}\n\n`;

        for (const [serverName, serverConfig] of Object.entries(config)) {
            yaml += `${serverName}:\n`;
            for (const [key, value] of Object.entries(serverConfig)) {
                yaml += `  ${key}: ${value}\n`;
            }
            yaml += '\n';
        }

        return yaml;
    }

    sendResponse(response) {
        console.log(JSON.stringify(response));
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
        
        console.log(JSON.stringify(error));
    }
}

// 启动服务器
if (require.main === module) {
    new RemoteTerminalMCPServer();
}

module.exports = RemoteTerminalMCPServer; 