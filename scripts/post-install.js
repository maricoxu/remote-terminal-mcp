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

    async createUserConfig() {
        this.log('Checking user configuration...');
        
        const homeDir = os.homedir();
        const configDir = path.join(homeDir, '.remote-terminal');
        const userConfig = path.join(configDir, 'config.yaml');
        const backupConfig = path.join(configDir, 'config.yaml.backup');
        const persistentBackup = path.join(homeDir, '.remote-terminal-config-backup.yaml');
        const markerFile = path.join(configDir, '.npm-installed');
        const persistentMarker = path.join(homeDir, '.remote-terminal-npm-installed');
        
        // 检查是否是npm包更新场景
        const isUpdate = (fs.existsSync(markerFile) || fs.existsSync(persistentMarker)) && fs.existsSync(userConfig);
        
        if (isUpdate) {
            this.log('Detected npm package update - preserving existing user configuration', 'success');
            this.log(`Existing configuration: ${userConfig}`, 'info');
            
            // 更新安装标记的时间戳
            const timestamp = new Date().toISOString();
            try {
                fs.writeFileSync(markerFile, timestamp, 'utf8');
                fs.writeFileSync(persistentMarker, timestamp, 'utf8');
                this.log('Updated installation markers', 'info');
            } catch (error) {
                this.warnings.push(`Failed to update installation markers: ${error.message}`);
            }
            
            return configDir;
        }
        
        // 首次安装或配置丢失的情况
        if (!fs.existsSync(configDir)) {
            fs.mkdirSync(configDir, { recursive: true });
            this.log(`Configuration directory created: ${configDir}`, 'success');
        }
        
        // 检查是否存在任何形式的用户配置
        const hasUserConfig = fs.existsSync(userConfig) || 
                             fs.existsSync(backupConfig) || 
                             fs.existsSync(persistentBackup);
        
        if (hasUserConfig) {
            this.log('Found existing user configuration - preserving user data', 'success');
            
            // 如果主配置文件不存在但有备份，尝试恢复
            if (!fs.existsSync(userConfig)) {
                if (fs.existsSync(backupConfig)) {
                    fs.copyFileSync(backupConfig, userConfig);
                    this.log('Restored configuration from local backup', 'success');
                } else if (fs.existsSync(persistentBackup)) {
                    fs.copyFileSync(persistentBackup, userConfig);
                    this.log('Restored configuration from persistent backup', 'success');
                }
            }
            
            // 创建安装标记
            const timestamp = new Date().toISOString();
            try {
                fs.writeFileSync(markerFile, timestamp, 'utf8');
                fs.writeFileSync(persistentMarker, timestamp, 'utf8');
                this.log('Created installation markers', 'info');
            } catch (error) {
                this.warnings.push(`Failed to create installation markers: ${error.message}`);
            }
            
            return configDir;
        }
        
        // 真正的首次安装 - 创建新配置
        this.log('First-time installation - creating new configuration', 'info');
        
        const configTemplate = path.join(packageRoot, 'templates', 'config.yaml.template');
        
        if (fs.existsSync(configTemplate)) {
            // Read template and replace timestamp
            let templateContent = fs.readFileSync(configTemplate, 'utf8');
            templateContent = templateContent.replace('{{ timestamp }}', new Date().toISOString());
            
            // Write to user config with explicit permissions
            fs.writeFileSync(userConfig, templateContent, { encoding: 'utf8', mode: 0o644 });
            
            // Verify the file was created
            if (fs.existsSync(userConfig)) {
                this.log(`Configuration template created: ${userConfig}`, 'success');
                this.log('Please edit the config.yaml file to add your server details', 'info');
                
                // Create backup copies
                try {
                    fs.copyFileSync(userConfig, backupConfig);
                    fs.copyFileSync(userConfig, persistentBackup);
                    this.log(`Backup configuration created: ${backupConfig}`, 'info');
                    this.log(`Persistent backup created: ${persistentBackup}`, 'info');
                } catch (error) {
                    this.warnings.push(`Failed to create backup copies: ${error.message}`);
                }
                
                // Create installation markers
                const timestamp = new Date().toISOString();
                try {
                    fs.writeFileSync(markerFile, timestamp, 'utf8');
                    fs.writeFileSync(persistentMarker, timestamp, 'utf8');
                    this.log(`Installation marker created: ${markerFile}`, 'info');
                    this.log(`Persistent marker created: ${persistentMarker}`, 'info');
                } catch (error) {
                    this.warnings.push(`Failed to create installation markers: ${error.message}`);
                }
            } else {
                this.warnings.push('Configuration file creation verification failed');
            }
        } else {
            this.log('Configuration template not found, creating basic config', 'warning');
            // Create a basic config if template is missing
            const basicConfig = `# Remote Terminal MCP Configuration
# Generated at: ${new Date().toISOString()}
# TEMPLATE ONLY - REPLACE VALUES BEFORE USE

servers:
  example-server:
    type: script_based
    host: "REPLACE_WITH_YOUR_SERVER_HOST"
    port: 22
    username: "REPLACE_WITH_YOUR_USERNAME"
    description: "示例服务器配置 - TEMPLATE ONLY, REPLACE VALUES BEFORE USE"
    session:
      name: "REPLACE_WITH_SESSION_NAME"
    specs:
      connection:
        type: ssh
        timeout: 30
      environment_setup:
        shell: bash
        working_directory: "REPLACE_WITH_WORKING_DIRECTORY"

global_settings:
  default_timeout: 30
  auto_recovery: true
  log_level: INFO

security_settings:
  strict_host_key_checking: false
  connection_timeout: 30
`;
            fs.writeFileSync(userConfig, basicConfig, 'utf8');
            this.log(`Basic configuration created: ${userConfig}`, 'success');
            
            // Create backup and markers
            try {
                fs.copyFileSync(userConfig, backupConfig);
                fs.copyFileSync(userConfig, persistentBackup);
                
                const timestamp = new Date().toISOString();
                fs.writeFileSync(markerFile, timestamp, 'utf8');
                fs.writeFileSync(persistentMarker, timestamp, 'utf8');
                this.log('Created backup copies and installation markers', 'info');
            } catch (error) {
                this.warnings.push(`Failed to create backup copies or markers: ${error.message}`);
            }
        }
        
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
        this.log('   1. Run: remote-terminal-mcp init', 'info');
        this.log('   2. Configure server information', 'info');
        this.log('   3. Configure MCP server in Cursor', 'info');
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
            await this.createUserConfig();
            
            // Wait a moment and recreate config if it was deleted
            await new Promise(resolve => setTimeout(resolve, 500));
            await this.ensureConfigExists();
            
            await this.showCompletion();
            
        } catch (error) {
            this.log(`Installation error: ${error.message}`, 'error');
            process.exit(1);
        }
    }

    async ensureConfigExists() {
        const homeDir = os.homedir();
        const configDir = path.join(homeDir, '.remote-terminal');
        const userConfig = path.join(configDir, 'config.yaml');
        const backupConfig = path.join(configDir, 'config.yaml.backup');
        
        if (!fs.existsSync(userConfig)) {
            this.log('Configuration file was deleted, recreating...', 'warning');
            
            if (fs.existsSync(backupConfig)) {
                // Restore from backup
                fs.copyFileSync(backupConfig, userConfig);
                this.log('Configuration restored from backup', 'success');
            } else {
                // Create basic config
                const basicConfig = `# Remote Terminal MCP Configuration
# Generated at: ${new Date().toISOString()}

servers:
  example-server:
    type: script_based
    host: example.com
    port: 22
    username: your-username
    description: 示例服务器配置 - 请修改为你的实际服务器信息
    session:
      name: example-server_dev
    specs:
      connection:
        type: ssh
        timeout: 30
      environment_setup:
        shell: bash
        working_directory: /home/your-username

global_settings:
  default_timeout: 30
  auto_recovery: true
  log_level: INFO

security_settings:
  strict_host_key_checking: false
  connection_timeout: 30
`;
                fs.writeFileSync(userConfig, basicConfig, 'utf8');
                this.log('Basic configuration recreated', 'success');
            }
        } else {
            this.log('Configuration file exists', 'success');
        }
    }
}

// 运行安装程序
const installer = new PostInstaller();
installer.run().catch(console.error);

module.exports = installer.run;