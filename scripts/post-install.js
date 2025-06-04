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

console.log('🚀 正在配置 Remote Terminal MCP...\n');

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
        this.log('🐍 检查Python环境...');
        
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
        
        this.log(`✅ 发现Python: ${pythonCmd}`, 'success');
        return pythonCmd;
    }

    async installPythonDeps(pythonCmd) {
        this.log('📦 安装Python依赖...');
        
        try {
            // 检查pip
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
            
            // 安装依赖
            execSync(`${pipCmd} install -r "${requirementsFile}"`, { 
                stdio: 'inherit',
                cwd: packageRoot 
            });
            
            this.log('✅ Python依赖安装完成', 'success');
            return true;
        } catch (error) {
            this.warnings.push(`Python依赖安装失败: ${error.message}`);
            this.log('⚠️  您可能需要手动运行: pip install -r requirements.txt', 'warning');
            return false;
        }
    }

    async checkTmux() {
        this.log('🖥️  检查tmux...');
        
        if (this.checkCommand('tmux')) {
            this.log('✅ tmux已安装', 'success');
            return true;
        }
        
        const installInstructions = {
            'darwin': 'brew install tmux',
            'linux': 'sudo apt install tmux  # 或 sudo yum install tmux',
            'default': 'Please install tmux for your system'
        };
        
        const instruction = installInstructions[this.platform] || installInstructions.default;
        this.warnings.push(`tmux not found. Install with: ${instruction}`);
        return false;
    }

    async setPermissions() {
        this.log('🔐 设置文件权限...');
        
        try {
            // 设置shell脚本执行权限
            const shellScripts = [
                path.join(templatesDir, 'connect_cpu_221.sh')
            ];
            
            for (const script of shellScripts) {
                if (fs.existsSync(script)) {
                    fs.chmodSync(script, '755');
                }
            }
            
            // 设置Python脚本执行权限
            const pythonScripts = [
                path.join(pythonDir, 'ssh_manager.py'),
                path.join(packageRoot, 'index.js')
            ];
            
            for (const script of pythonScripts) {
                if (fs.existsSync(script)) {
                    fs.chmodSync(script, '755');
                }
            }
            
            this.log('✅ 文件权限设置完成', 'success');
            return true;
        } catch (error) {
            this.warnings.push(`权限设置失败: ${error.message}`);
            return false;
        }
    }

    async createUserConfig() {
        this.log('⚙️  创建用户配置目录...');
        
        const homeDir = os.homedir();
        const configDir = path.join(homeDir, '.remote-terminal-mcp');
        
        if (!fs.existsSync(configDir)) {
            fs.mkdirSync(configDir, { recursive: true });
            this.log(`✅ 配置目录创建: ${configDir}`, 'success');
        }
        
        // 复制配置模板
        const configTemplate = path.join(packageRoot, 'config', 'servers.json');
        const userConfig = path.join(configDir, 'servers.json');
        
        if (fs.existsSync(configTemplate) && !fs.existsSync(userConfig)) {
            fs.copyFileSync(configTemplate, userConfig);
            this.log(`✅ 配置模板复制到: ${userConfig}`, 'success');
        }
        
        return configDir;
    }

    async showCompletion() {
        this.log('\n🎉 安装完成!\n', 'success');
        
        if (this.errors.length > 0) {
            this.log('❌ 错误:', 'error');
            this.errors.forEach(error => this.log(`   • ${error}`, 'error'));
            this.log('');
        }
        
        if (this.warnings.length > 0) {
            this.log('⚠️  警告:', 'warning');
            this.warnings.forEach(warning => this.log(`   • ${warning}`, 'warning'));
            this.log('');
        }
        
        this.log('📖 下一步:', 'info');
        this.log('   1. 运行: remote-terminal-mcp init', 'info');
        this.log('   2. 配置服务器信息', 'info');
        this.log('   3. 在Cursor中配置MCP服务器', 'info');
        this.log('');
        this.log('📚 详细文档: https://github.com/maricoxu/remote-terminal-mcp', 'info');
    }

    async run() {
        try {
            const pythonCmd = await this.checkPython();
            
            if (pythonCmd) {
                await this.installPythonDeps(pythonCmd);
            }
            
            await this.checkTmux();
            await this.setPermissions();
            await this.createUserConfig();
            await this.showCompletion();
            
        } catch (error) {
            this.log(`💥 安装过程中出现错误: ${error.message}`, 'error');
            process.exit(1);
        }
    }
}

// 运行安装程序
const installer = new PostInstaller();
installer.run().catch(console.error);

module.exports = installer.run;