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
                bos_bucket: 'bos:/klx-pytorch-work-bd-bj/xuyehua/template',
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
                // HG系列服务器 (Tesla A100)
                hg_223: {
                    name: 'HG-223 GPU服务器',
                    host: 'bjhw-sys-gpu0223.bjhw',
                    jump_host: 'jumper.baidu.com',
                    container_name: 'xyh_pytorch',
                    gpu_type: 'Tesla A100',
                    gpu_count: 8,
                    series: 'HG',
                    location: 'Beijing',
                    status: 'active'
                },
                hg_224: {
                    name: 'HG-224 GPU服务器',
                    host: 'bjhw-sys-gpu0224.bjhw',
                    jump_host: 'jumper.baidu.com',
                    container_name: 'xyh_pytorch',
                    gpu_type: 'Tesla A100',
                    gpu_count: 8,
                    series: 'HG',
                    location: 'Beijing',
                    status: 'active'
                },
                hg_225: {
                    name: 'HG-225 GPU服务器',
                    host: 'bjhw-sys-gpu0225.bjhw',
                    jump_host: 'jumper.baidu.com',
                    container_name: 'xyh_pytorch',
                    gpu_type: 'Tesla A100',
                    gpu_count: 8,
                    series: 'HG',
                    location: 'Beijing',
                    status: 'active'
                },
                hg_226: {
                    name: 'HG-226 GPU服务器',
                    host: 'bjhw-sys-gpu0226.bjhw',
                    jump_host: 'jumper.baidu.com',
                    container_name: 'xyh_pytorch',
                    gpu_type: 'Tesla A100',
                    gpu_count: 8,
                    series: 'HG',
                    location: 'Beijing',
                    status: 'active'
                },
                
                // TJ系列服务器 (Tesla V100)
                tj_041: {
                    name: 'TJ-041 GPU服务器',
                    host: 'cp01-rd-gpu-tj041.ecom',
                    container_name: 'xyh_pytorch',
                    gpu_type: 'Tesla V100',
                    gpu_count: 8,
                    series: 'TJ',
                    location: 'Tianjin',
                    status: 'active'
                },
                tj_042: {
                    name: 'TJ-042 GPU服务器',
                    host: 'cp01-rd-gpu-tj042.ecom',
                    container_name: 'xyh_pytorch',
                    gpu_type: 'Tesla V100',
                    gpu_count: 8,
                    series: 'TJ',
                    location: 'Tianjin',
                    status: 'active'
                },
                tj_043: {
                    name: 'TJ-043 GPU服务器',
                    host: 'cp01-rd-gpu-tj043.ecom',
                    container_name: 'xyh_pytorch',
                    gpu_type: 'Tesla V100',
                    gpu_count: 8,
                    series: 'TJ',
                    location: 'Tianjin',
                    status: 'active'
                },
                tj_044: {
                    name: 'TJ-044 GPU服务器',
                    host: 'cp01-rd-gpu-tj044.ecom',
                    container_name: 'xyh_pytorch',
                    gpu_type: 'Tesla V100',
                    gpu_count: 8,
                    series: 'TJ',
                    location: 'Tianjin',
                    status: 'active'
                },

                // CPU系列服务器
                cpu_221: {
                    name: 'CPU-221 计算服务器',
                    host: 'bjhw-sys-rpm0221.bjhw',
                    container_name: 'xyh_pytorch',
                    gpu_type: 'None',
                    gpu_count: 0,
                    series: 'CPU',
                    location: 'Beijing',
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