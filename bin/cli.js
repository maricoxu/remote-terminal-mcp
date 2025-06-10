#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

class RemoteTerminalCLI {
    constructor() {
        this.homeDir = os.homedir();
        this.configDir = path.join(this.homeDir, '.remote-terminal-mcp');
        this.configFile = path.join(this.configDir, 'servers.json');
        this.packageRoot = path.resolve(__dirname, '..');
    }

    log(message, type = 'info') {
        const colors = {
            info: '\x1b[36m',      // cyan
            success: '\x1b[32m',   // green
            warning: '\x1b[33m',   // yellow
            error: '\x1b[31m',     // red
            reset: '\x1b[0m'
        };
        console.log(`${colors[type]}${message}${colors.reset}`);
    }

    showHelp() {
        console.log(`
🚀 Remote Terminal MCP CLI

Usage: remote-terminal-mcp <command> [options]

Commands:
  init      Initialize configuration files
  config    Configure server information
  start     Start MCP server
  doctor    Diagnose environment issues
  help      Show help information

Examples:
  remote-terminal-mcp init
  remote-terminal-mcp config
  remote-terminal-mcp start
  remote-terminal-mcp doctor

Documentation: https://github.com/maricoxu/remote-terminal-mcp
        `);
    }

    async init() {
        this.log('Initializing Remote Terminal MCP...');

        // Create config directory
        if (!fs.existsSync(this.configDir)) {
            fs.mkdirSync(this.configDir, { recursive: true });
            this.log(`Config directory created: ${this.configDir}`, 'success');
        }

        // Copy config template
        const templatePath = path.join(this.packageRoot, 'config', 'servers.json');
        
        if (fs.existsSync(this.configFile)) {
            this.log('Config file already exists, skipping initialization', 'warning');
            this.log(`   Location: ${this.configFile}`);
        } else if (fs.existsSync(templatePath)) {
            fs.copyFileSync(templatePath, this.configFile);
            this.log(`Config file created: ${this.configFile}`, 'success');
        } else {
            // Create default config
            const defaultConfig = {
                "servers": {
                    "example-server": {
                        "mode": "direct",
                        "connection": {
                            "host": "your-server.com",
                            "port": 22,
                            "username": "your-username",
                            "password": "your-password"
                        },
                        "docker": {
                            "enabled": false,
                            "container_name": "your-container"
                        },
                        "tmux": {
                            "session_name": "dev-session",
                            "auto_create": true
                        }
                    }
                }
            };
            
            fs.writeFileSync(this.configFile, JSON.stringify(defaultConfig, null, 2));
            this.log(`Default config file created: ${this.configFile}`, 'success');
        }

        // Generate Cursor MCP config
        await this.generateCursorConfig();

        this.log('\nNext steps:', 'info');
        this.log('   1. Edit config file: ' + this.configFile, 'info');
        this.log('   2. Run: remote-terminal-mcp config', 'info');
        this.log('   3. Reload MCP server in Cursor', 'info');
    }

    async generateCursorConfig() {
        const cursorConfigDir = path.join(this.homeDir, '.cursor');
        const cursorMcpFile = path.join(cursorConfigDir, 'mcp.json');
        
        const mcpConfig = {
            mcpServers: {
                "remote-terminal": {
                    command: "npx",
                    args: ["-y", "@xuyehua/remote-terminal-mcp"],
                    disabled: false,
                    autoApprove: true
                }
            }
        };

        if (!fs.existsSync(cursorConfigDir)) {
            fs.mkdirSync(cursorConfigDir, { recursive: true });
        }

        let existingConfig = {};
        if (fs.existsSync(cursorMcpFile)) {
            try {
                existingConfig = JSON.parse(fs.readFileSync(cursorMcpFile, 'utf8'));
            } catch (error) {
                this.log('Warning: Failed to read existing Cursor config, will create new one', 'warning');
            }
        }

        // 合并配置
        if (!existingConfig.mcpServers) {
            existingConfig.mcpServers = {};
        }
        existingConfig.mcpServers['remote-terminal'] = mcpConfig.mcpServers['remote-terminal'];

        fs.writeFileSync(cursorMcpFile, JSON.stringify(existingConfig, null, 2));
        this.log(`Cursor MCP config updated: ${cursorMcpFile}`, 'success');
    }

    async config() {
        this.log('⚙️  Configure server information...');

        if (!fs.existsSync(this.configFile)) {
            this.log('Config file not found, please run: remote-terminal-mcp init', 'error');
            return;
        }

        this.log(`Please edit config file: ${this.configFile}`);
        this.log('\nConfiguration examples:');
        console.log(`{
  "servers": {
    "my-server": {
      "mode": "direct",  // or "jump_host", "double_jump_host"
      "connection": {
        "host": "192.168.1.100",
        "port": 22,
        "username": "root",
        "password": "your-password"
      },
      "docker": {
        "enabled": true,
        "container_name": "dev-container"
      },
      "tmux": {
        "session_name": "dev-session",
        "auto_create": true
      }
    }
  }
}`);

        this.log('\nFor more configuration options, see documentation');
    }

    async start() {
        const isMCPCall = !process.stdin.isTTY;
        
        if (!isMCPCall) {
            this.log('Starting MCP server...');
        }
        
        try {
            const indexPath = path.join(this.packageRoot, 'index.js');
            const RemoteTerminalMCP = require(indexPath);
            const terminal = new RemoteTerminalMCP();
            
            terminal.main().catch(error => {
                if (!isMCPCall) {
                    this.log(`Startup failed: ${error.message}`, 'error');
                }
                process.exit(1);
            });

            // This is the key: return a promise that never resolves.
            // This keeps the cli.js script (the main process) alive.
            return new Promise(() => {});

        } catch (error) {
            if (!isMCPCall) {
                this.log(`Startup failed: ${error.message}`, 'error');
            }
            process.exit(1);
        }
    }

    async doctor() {
        this.log('Environment diagnosis...\n');

        let allGood = true;

        // 检查Node.js
        try {
            const nodeVersion = process.version;
            this.log(`✅ Node.js: ${nodeVersion}`, 'success');
        } catch (error) {
            this.log('Node.js version check failed', 'error');
            allGood = false;
        }

        // 检查Python
        try {
            const pythonVersion = execSync('python3 --version', { encoding: 'utf8' }).trim();
            this.log(`✅ Python: ${pythonVersion}`, 'success');
        } catch (error) {
            try {
                const pythonVersion = execSync('python --version', { encoding: 'utf8' }).trim();
                this.log(`✅ Python: ${pythonVersion}`, 'success');
            } catch {
                this.log('Python not installed or not in PATH', 'error');
                this.log('   Please install Python 3.6+: https://python.org', 'info');
                allGood = false;
            }
        }

        // 检查pip
        try {
            execSync('pip --version', { stdio: 'ignore' });
            this.log('pip installed', 'success');
        } catch (error) {
            this.log('pip not installed, may affect Python dependency management', 'warning');
        }

        // 检查tmux
        try {
            const tmuxVersion = execSync('tmux -V', { encoding: 'utf8' }).trim();
            this.log(`✅ tmux: ${tmuxVersion}`, 'success');
        } catch (error) {
            this.log('tmux not installed', 'warning');
            const platform = os.platform();
            const installCmd = platform === 'darwin' ? 'brew install tmux' : 'sudo apt install tmux';
            this.log(`   Install: ${installCmd}`, 'info');
        }

        // 检查配置文件
        if (fs.existsSync(this.configFile)) {
            this.log(`Config file: ${this.configFile}`, 'success');
            
            try {
                const config = JSON.parse(fs.readFileSync(this.configFile, 'utf8'));
                const serverCount = Object.keys(config.servers || {}).length;
                this.log(`   Number of configured servers: ${serverCount}`, 'info');
            } catch (error) {
                this.log('Config file format error', 'error');
                this.log('   Please check JSON syntax', 'info');
                allGood = false;
            }
        } else {
            this.log('Config file does not exist', 'warning');
            this.log('   Run: remote-terminal-mcp init', 'info');
        }

        // Check Cursor config
        const cursorMcpFile = path.join(this.homeDir, '.cursor', 'mcp.json');
        if (fs.existsSync(cursorMcpFile)) {
            this.log(`Cursor MCP config: ${cursorMcpFile}`, 'success');
        } else {
            this.log('Cursor MCP config does not exist', 'warning');
            this.log('   Run: remote-terminal-mcp init', 'info');
        }

        this.log('\n' + (allGood ? 'Environment check completed, everything is normal!' : 'Some issues found, please follow the prompts to resolve'));
    }

    async run() {
        const args = process.argv.slice(2);
        const command = args[0];
        const commands = {
            init: this.init.bind(this),
            config: this.config.bind(this),
            start: this.start.bind(this),
            doctor: this.doctor.bind(this),
            help: this.showHelp.bind(this)
        };

        if (command) {
            if (commands[command]) {
                await commands[command]();
            } else {
                this.log(`Unknown command: ${command}`, 'error');
                this.showHelp();
                process.exit(1);
            }
        } else {
            if (process.stdin.isTTY) {
                this.showHelp();
            } else {
                await this.start();
            }
        }
    }
}

const cli = new RemoteTerminalCLI();
cli.run().catch(error => {
    console.error(`Unhandled rejection in CLI: ${error.message}`);
    process.exit(1);
}); 