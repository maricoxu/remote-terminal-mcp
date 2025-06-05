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

用法: remote-terminal-mcp <命令> [选项]

命令:
  init      初始化配置文件
  config    配置服务器信息
  start     Start MCP server
  doctor    诊断环境问题
  help      显示帮助信息

示例:
  remote-terminal-mcp init
  remote-terminal-mcp config
  remote-terminal-mcp start
  remote-terminal-mcp doctor

文档: https://github.com/maricoxu/remote-terminal-mcp
        `);
    }

    async init() {
        this.log('🔧 初始化 Remote Terminal MCP...');

        // 创建配置目录
        if (!fs.existsSync(this.configDir)) {
            fs.mkdirSync(this.configDir, { recursive: true });
            this.log(`✅ 配置目录创建: ${this.configDir}`, 'success');
        }

        // 复制配置模板
        const templatePath = path.join(this.packageRoot, 'config', 'servers.json');
        
        if (fs.existsSync(this.configFile)) {
            this.log('⚠️  配置文件已存在，跳过初始化', 'warning');
            this.log(`   位置: ${this.configFile}`);
        } else if (fs.existsSync(templatePath)) {
            fs.copyFileSync(templatePath, this.configFile);
            this.log(`✅ 配置文件创建: ${this.configFile}`, 'success');
        } else {
            // 创建默认配置
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
            this.log(`✅ 默认配置文件创建: ${this.configFile}`, 'success');
        }

        // 生成Cursor MCP配置
        await this.generateCursorConfig();

        this.log('\n📖 下一步:', 'info');
        this.log('   1. 编辑配置文件: ' + this.configFile, 'info');
        this.log('   2. 运行: remote-terminal-mcp config', 'info');
        this.log('   3. 在Cursor中重新加载MCP服务器', 'info');
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
        this.log(`✅ Cursor MCP配置更新: ${cursorMcpFile}`, 'success');
    }

    async config() {
        this.log('⚙️  配置服务器信息...');

        if (!fs.existsSync(this.configFile)) {
            this.log('❌ 配置文件不存在，请先运行: remote-terminal-mcp init', 'error');
            return;
        }

        this.log(`📝 请编辑配置文件: ${this.configFile}`);
        this.log('\n配置示例:');
        console.log(`{
  "servers": {
    "my-server": {
      "mode": "direct",  // 或 "jump_host", "double_jump_host"
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

        this.log('\n📖 更多配置选项请参考文档');
    }

    async start() {
        // 检查是否是从Cursor/MCP调用（通过stdin检测）
        const isMCPCall = !process.stdin.isTTY;
        
        if (!isMCPCall) {
            this.log('Starting MCP server...');
        }
        
        try {
            const indexPath = path.join(this.packageRoot, 'index.js');
            require(indexPath);
        } catch (error) {
            if (!isMCPCall) {
                this.log(`Startup failed: ${error.message}`, 'error');
            }
            process.exit(1);
        }
    }

    async doctor() {
        this.log('🔍 环境诊断...\n');

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
                this.log('❌ Python未安装或不在PATH中', 'error');
                this.log('   请安装Python 3.6+: https://python.org', 'info');
                allGood = false;
            }
        }

        // 检查pip
        try {
            execSync('pip --version', { stdio: 'ignore' });
            this.log('✅ pip已安装', 'success');
        } catch (error) {
            this.log('⚠️  pip未安装，可能影响Python依赖管理', 'warning');
        }

        // 检查tmux
        try {
            const tmuxVersion = execSync('tmux -V', { encoding: 'utf8' }).trim();
            this.log(`✅ tmux: ${tmuxVersion}`, 'success');
        } catch (error) {
            this.log('⚠️  tmux未安装', 'warning');
            const platform = os.platform();
            const installCmd = platform === 'darwin' ? 'brew install tmux' : 'sudo apt install tmux';
            this.log(`   安装: ${installCmd}`, 'info');
        }

        // 检查配置文件
        if (fs.existsSync(this.configFile)) {
            this.log(`✅ 配置文件: ${this.configFile}`, 'success');
            
            try {
                const config = JSON.parse(fs.readFileSync(this.configFile, 'utf8'));
                const serverCount = Object.keys(config.servers || {}).length;
                this.log(`   配置的服务器数量: ${serverCount}`, 'info');
            } catch (error) {
                this.log('❌ 配置文件格式错误', 'error');
                this.log('   请检查JSON语法', 'info');
                allGood = false;
            }
        } else {
            this.log('⚠️  配置文件不存在', 'warning');
            this.log('   运行: remote-terminal-mcp init', 'info');
        }

        // 检查Cursor配置
        const cursorMcpFile = path.join(this.homeDir, '.cursor', 'mcp.json');
        if (fs.existsSync(cursorMcpFile)) {
            this.log(`✅ Cursor MCP配置: ${cursorMcpFile}`, 'success');
        } else {
            this.log('⚠️  Cursor MCP配置不存在', 'warning');
            this.log('   运行: remote-terminal-mcp init', 'info');
        }

        this.log('\n' + (allGood ? '🎉 环境检查完成，一切正常！' : '⚠️  发现一些问题，请按提示解决'));
    }

    run() {
        const args = process.argv.slice(2);
        const command = args[0];

        switch (command) {
            case 'init':
                this.init();
                break;
            case 'config':
                this.config();
                break;
            case 'start':
                this.start();
                break;
            case 'doctor':
                this.doctor();
                break;
            case 'help':
            case '--help':
            case '-h':
                this.showHelp();
                break;
            default:
                if (!command) {
                    this.start(); // 默认启动MCP服务器
                } else {
                    this.log(`❌ 未知命令: ${command}`, 'error');
                    this.showHelp();
                    process.exit(1);
                }
        }
    }
}

const cli = new RemoteTerminalCLI();
cli.run(); 