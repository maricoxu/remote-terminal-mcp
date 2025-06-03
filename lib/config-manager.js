const fs = require('fs');
const path = require('path');
const os = require('os');
const yaml = require('yaml');
const inquirer = require('inquirer');
const chalk = require('chalk');

/**
 * 配置管理器 - 处理cursor-bridge的配置文件
 */
class ConfigManager {
    constructor() {
        this.configDir = path.join(os.homedir(), '.cursor-bridge');
        this.configFile = path.join(this.configDir, 'config.yaml');
        this.serversConfigFile = path.join(this.configDir, 'servers.yaml');
    }

    /**
     * 确保配置目录和文件存在
     */
    async ensureConfig() {
        // 创建配置目录
        if (!fs.existsSync(this.configDir)) {
            fs.mkdirSync(this.configDir, { recursive: true });
            console.log(chalk.blue('📁 创建配置目录:'), this.configDir);
        }

        // 检查主配置文件
        if (!fs.existsSync(this.configFile)) {
            await this.createInitialConfig();
        }

        // 检查服务器配置文件
        if (!fs.existsSync(this.serversConfigFile)) {
            await this.createServersConfig();
        }

        return {
            configFile: this.configFile,
            serversConfigFile: this.serversConfigFile
        };
    }

    /**
     * 创建初始配置文件
     */
    async createInitialConfig() {
        console.log(chalk.yellow('🔧 首次使用，创建默认配置...'));

        const defaultConfig = {
            version: '0.1.0',
            settings: {
                default_tmux_session: 'default',
                auto_create_session: true,
                debug_mode: false,
                storage_path: 'your-storage-path-here',  // 🔧 请修改为你的实际存储路径
                connection_timeout: 30,
                retry_attempts: 3
            },
            preferences: {
                show_gpu_info: true,
                auto_attach_tmux: false,
                preferred_shell: 'zsh'
            }
        };

        const yamlContent = yaml.stringify(defaultConfig, {
            indent: 2,
            quotingType: '"'
        });

        fs.writeFileSync(this.configFile, yamlContent);
        console.log(chalk.green('✅ 默认配置已创建'));
    }

    /**
     * 创建服务器配置文件
     */
    async createServersConfig() {
        const serversConfig = {
            servers: {
                // 示例GPU服务器配置
                gpu_server_1: {
                    name: 'GPU Server 1',
                    host: 'gpu-server-1.example.com',
                    jump_host: 'jumphost.example.com',
                    container_name: 'user_container',
                    gpu_type: 'Tesla A100',
                    gpu_count: 8,
                    series: 'GPU',
                    location: 'DataCenter-A',
                    status: 'active'
                },
                gpu_server_2: {
                    name: 'GPU Server 2',
                    host: 'gpu-server-2.example.com',
                    jump_host: 'jumphost.example.com',
                    container_name: 'user_container',
                    gpu_type: 'Tesla A100',
                    gpu_count: 8,
                    series: 'GPU',
                    location: 'DataCenter-A',
                    status: 'active'
                },
                gpu_server_3: {
                    name: 'GPU Server 3',
                    host: 'gpu-server-3.example.com',
                    jump_host: 'jumphost.example.com',
                    container_name: 'user_container',
                    gpu_type: 'Tesla A100',
                    gpu_count: 8,
                    series: 'GPU',
                    location: 'DataCenter-A',
                    status: 'active'
                },
                gpu_server_4: {
                    name: 'GPU Server 4',
                    host: 'gpu-server-4.example.com',
                    jump_host: 'jumphost.example.com',
                    container_name: 'user_container',
                    gpu_type: 'Tesla A100',
                    gpu_count: 8,
                    series: 'GPU',
                    location: 'DataCenter-A',
                    status: 'active'
                },
                
                // 示例训练服务器配置
                train_server_1: {
                    name: 'Training Server 1',
                    host: 'train-server-1.example.com',
                    container_name: 'user_container',
                    gpu_type: 'Tesla V100',
                    gpu_count: 8,
                    series: 'TRAIN',
                    location: 'DataCenter-B',
                    status: 'active'
                },
                train_server_2: {
                    name: 'Training Server 2',
                    host: 'train-server-2.example.com',
                    container_name: 'user_container',
                    gpu_type: 'Tesla V100',
                    gpu_count: 8,
                    series: 'TRAIN',
                    location: 'DataCenter-B',
                    status: 'active'
                },
                train_server_3: {
                    name: 'Training Server 3',
                    host: 'train-server-3.example.com',
                    container_name: 'user_container',
                    gpu_type: 'Tesla V100',
                    gpu_count: 8,
                    series: 'TRAIN',
                    location: 'DataCenter-B',
                    status: 'active'
                },
                train_server_4: {
                    name: 'Training Server 4',
                    host: 'train-server-4.example.com',
                    container_name: 'user_container',
                    gpu_type: 'Tesla V100',
                    gpu_count: 8,
                    series: 'TRAIN',
                    location: 'DataCenter-B',
                    status: 'active'
                },

                // CPU服务器示例
                cpu_server_1: {
                    name: 'CPU Server 1',
                    host: 'cpu-server-1.example.com',
                    container_name: 'user_container',
                    gpu_type: 'None',
                    gpu_count: 0,
                    series: 'CPU',
                    location: 'DataCenter-C',
                    status: 'active'
                }
            }
        };

        const yamlContent = yaml.stringify(serversConfig, {
            indent: 2,
            quotingType: '"'
        });

        fs.writeFileSync(this.serversConfigFile, yamlContent);
        console.log(chalk.green('✅ 服务器配置已创建'));
        console.log(chalk.yellow('⚠️  请修改配置文件中的示例服务器信息为你的实际配置'));
    }

    /**
     * 读取配置
     */
    readConfig() {
        try {
            const configContent = fs.readFileSync(this.configFile, 'utf8');
            return yaml.parse(configContent);
        } catch (error) {
            console.error(chalk.red('❌ 读取配置文件失败:'), error.message);
            return null;
        }
    }

    /**
     * 读取服务器配置
     */
    readServersConfig() {
        try {
            const configContent = fs.readFileSync(this.serversConfigFile, 'utf8');
            return yaml.parse(configContent);
        } catch (error) {
            console.error(chalk.red('❌ 读取服务器配置失败:'), error.message);
            return null;
        }
    }

    /**
     * 更新配置
     */
    updateConfig(newConfig) {
        try {
            const yamlContent = yaml.stringify(newConfig, {
                indent: 2,
                quotingType: '"'
            });
            fs.writeFileSync(this.configFile, yamlContent);
            console.log(chalk.green('✅ 配置已更新'));
            return true;
        } catch (error) {
            console.error(chalk.red('❌ 更新配置失败:'), error.message);
            return false;
        }
    }

    /**
     * 列出所有服务器
     */
    listServers() {
        const serversConfig = this.readServersConfig();
        if (!serversConfig || !serversConfig.servers) {
            return [];
        }

        return Object.entries(serversConfig.servers).map(([id, config]) => ({
            id,
            ...config
        }));
    }

    /**
     * 获取特定服务器配置
     */
    getServerConfig(serverId) {
        const serversConfig = this.readServersConfig();
        if (!serversConfig || !serversConfig.servers) {
            return null;
        }

        return serversConfig.servers[serverId] || null;
    }

    /**
     * 配置向导
     */
    async runConfigWizard() {
        console.log(chalk.blue('\n🧙‍♂️ Cursor-Bridge 配置向导'));
        console.log('帮助您个性化配置cursor-bridge\n');

        const config = this.readConfig();
        
        const answers = await inquirer.prompt([
            {
                type: 'input',
                name: 'defaultSession',
                message: '默认tmux会话名称:',
                default: config.settings?.default_tmux_session || 'default'
            },
            {
                type: 'confirm',
                name: 'autoCreateSession',
                message: '自动创建tmux会话?',
                default: config.settings?.auto_create_session || true
            },
            {
                type: 'confirm',
                name: 'showGpuInfo',
                message: '显示GPU信息?',
                default: config.preferences?.show_gpu_info || true
            },
            {
                type: 'list',
                name: 'shell',
                message: '首选Shell:',
                choices: ['zsh', 'bash', 'fish'],
                default: config.preferences?.preferred_shell || 'zsh'
            }
        ]);

        // 更新配置
        if (!config.settings) config.settings = {};
        if (!config.preferences) config.preferences = {};
        
        config.settings.default_tmux_session = answers.defaultSession;
        config.settings.auto_create_session = answers.autoCreateSession;
        config.preferences.show_gpu_info = answers.showGpuInfo;
        config.preferences.preferred_shell = answers.shell;

        this.updateConfig(config);
        console.log(chalk.green('\n✅ 配置已保存！'));
    }
}

module.exports = ConfigManager;