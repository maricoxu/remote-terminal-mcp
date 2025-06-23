#!/usr/bin/env node

/**
 * NPM包安装后脚本
 * 检查环境并提供使用指导
 */

// const chalk = require('chalk'); // 使用内置颜色输出
const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// 检查是否在MCP运行时（静默模式）
const isMCPMode = process.env.MCP_QUIET || process.argv.includes('--mcp-mode');
if (!isMCPMode) {
    console.log('Configuring Remote Terminal MCP...\n');
}

// 获取包安装目录
const packageRoot = path.resolve(__dirname, '..');
const pythonDir = path.join(packageRoot, 'python');
const templatesDir = path.join(packageRoot, 'templates');
const requirementsFile = path.join(packageRoot, 'requirements.txt');

class PostInstaller {
    constructor() {
        this.platform = os.platform();
        this.errors = [];
        this.warnings = [];
    }

    log(message, type = 'info') {
        // 在MCP运行时保持静默
        const isMCPMode = process.env.MCP_QUIET || process.argv.includes('--mcp-mode');
        if (isMCPMode) return;
        
        const colors = {
            info: '\x1b[36m',      // cyan
            success: '\x1b[32m',   // green
            warning: '\x1b[33m',   // yellow
            error: '\x1b[31m',     // red
            reset: '\x1b[0m'
        };
        console.log(`${colors[type]}${message}${colors.reset}`);
    }

    checkCommand(command) {
        try {
            execSync(`which ${command}`, { stdio: 'ignore' });
            return true;
        } catch {
            return false;
        }
    }

    async checkPython() {
        this.log('Checking Python environment...');
        
        const pythonCommands = ['python3', 'python'];
        let pythonCmd = null;
        
        for (const cmd of pythonCommands) {
            if (this.checkCommand(cmd)) {
                pythonCmd = cmd;
                break;
            }
        }
        
        if (!pythonCmd) {
            this.errors.push('Python not found. Please install Python 3.6+');
            return false;
        }
        
        this.log(`Python found: ${pythonCmd}`, 'success');
        return pythonCmd;
    }

    async installPythonDeps(pythonCmd) {
        this.log('Installing Python dependencies...');
        
        try {
            // Check pip
            const pipCommands = [`${pythonCmd} -m pip`, 'pip3', 'pip'];
            let pipCmd = null;
            
            for (const cmd of pipCommands) {
                try {
                    execSync(`${cmd} --version`, { stdio: 'ignore' });
                    pipCmd = cmd;
                    break;
                } catch {}
            }
            
            if (!pipCmd) {
                this.warnings.push('pip not found. Please install pip manually');
                return false;
            }
            
            // Install dependencies
            execSync(`${pipCmd} install -r "${requirementsFile}"`, { 
                stdio: 'inherit',
                cwd: packageRoot 
            });
            
            this.log('Python dependencies installed successfully', 'success');
            return true;
        } catch (error) {
            this.warnings.push(`Python dependency installation failed: ${error.message}`);
            this.log('You may need to manually run: pip install -r requirements.txt', 'warning');
            return false;
        }
    }

    async checkTmux() {
        this.log('Checking tmux...');
        
        if (this.checkCommand('tmux')) {
            this.log('tmux is installed', 'success');
            return true;
        }
        
        const installInstructions = {
            'darwin': 'brew install tmux',
            'linux': 'sudo apt install tmux  # or sudo yum install tmux',
            'default': 'Please install tmux for your system'
        };
        
        const instruction = installInstructions[this.platform] || installInstructions.default;
        this.warnings.push(`tmux not found. Install with: ${instruction}`);
        return false;
    }

    async setPermissions() {
        this.log('Setting file permissions...');
        
        try {
            // Set shell script execution permissions
            const shellScripts = [
                path.join(templatesDir, 'connect_cpu_221.sh')
            ];
            
            for (const script of shellScripts) {
                if (fs.existsSync(script)) {
                    fs.chmodSync(script, '755');
                }
            }
            
            // Set Python script execution permissions
            const pythonScripts = [
                path.join(pythonDir, 'ssh_manager.py'),
                path.join(packageRoot, 'index.js')
            ];
            
            for (const script of pythonScripts) {
                if (fs.existsSync(script)) {
                    fs.chmodSync(script, '755');
                }
            }
            
            this.log('File permissions set successfully', 'success');
            return true;
        } catch (error) {
            this.warnings.push(`Permission setting failed: ${error.message}`);
            return false;
        }
    }

    async checkUserConfig() {
        this.log('Checking user configuration...');
        
        const homeDir = os.homedir();
        const configDir = path.join(homeDir, '.remote-terminal');
        const userConfig = path.join(configDir, 'config.yaml');
        
        // 只检查是否存在配置，不自动创建
        if (fs.existsSync(userConfig)) {
            this.log('Found existing user configuration', 'success');
            this.log(`Configuration location: ${userConfig}`, 'info');
            return configDir;
        }
        
        // 确保配置目录存在（但不创建配置文件）
        if (!fs.existsSync(configDir)) {
            fs.mkdirSync(configDir, { recursive: true });
            this.log(`Configuration directory created: ${configDir}`, 'success');
        }
        
        this.log('No configuration file found - user will need to create one', 'info');
        this.log(`Configuration should be created at: ${userConfig}`, 'info');
        
        return configDir;
    }

    async showCompletion() {
        this.log('\nInstallation completed!\n', 'success');
        
        if (this.errors.length > 0) {
            this.log('Errors:', 'error');
            this.errors.forEach(error => this.log(`   • ${error}`, 'error'));
            this.log('');
        }
        
        if (this.warnings.length > 0) {
            this.log('Warnings:', 'warning');
            this.warnings.forEach(warning => this.log(`   • ${warning}`, 'warning'));
            this.log('');
        }
        
        this.log('Next steps:', 'info');
        this.log('   1. Add MCP server to Cursor (see documentation)', 'info');
        this.log('   2. In Cursor, say: "我想新增一个远程服务器"', 'info');
        this.log('   3. AI will guide you through the configuration process', 'info');
        this.log('');
        this.log('No default configuration file is created to avoid npm update conflicts.', 'info');
        this.log('Use the AI assistant in Cursor to create your server configurations.', 'info');
        this.log('');
        this.log('Documentation: https://github.com/maricoxu/remote-terminal-mcp', 'info');
    }

    async run() {
        try {
            const pythonCmd = await this.checkPython();
            
            if (pythonCmd) {
                await this.installPythonDeps(pythonCmd);
            }
            
            await this.checkTmux();
            await this.setPermissions();
            await this.checkUserConfig();
            
            await this.showCompletion();
            
        } catch (error) {
            this.log(`Installation error: ${error.message}`, 'error');
            process.exit(1);
        }
    }


}

// 运行安装程序
const installer = new PostInstaller();
installer.run().catch(console.error);

module.exports = installer.run;