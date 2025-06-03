#!/usr/bin/env node

/**
 * Remote Terminal MCP NPM Package
 * 统一远程终端管理的MCP服务 - 让多服务器操作如本地一样简单
 * 
 * @author xuyehua
 * @version 0.1.0
 */

const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const chalk = require('chalk');
const ora = require('ora');

const ConfigManager = require('./lib/config-manager');
const EnvironmentChecker = require('./lib/environment-checker');
const ScriptGenerator = require('./lib/script-generator');

class RemoteTerminalMCP {
    constructor() {
        this.packageDir = __dirname;
        this.pythonDir = path.join(this.packageDir, 'python');
        this.configManager = new ConfigManager();
        this.envChecker = new EnvironmentChecker();
        this.scriptGenerator = new ScriptGenerator(this.configManager);
        
        // 解析命令行参数
        this.args = this.parseArgs();
    }

    /**
     * 解析命令行参数
     */
    parseArgs() {
        const args = process.argv.slice(2);
        return {
            isTestMode: args.includes('--test') || args.includes('-t'),
            isDebugMode: args.includes('--debug') || args.includes('-d'),
            isConfigMode: args.includes('--config') || args.includes('-c'),
            isVersionMode: args.includes('--version') || args.includes('-v'),
            isHelpMode: args.includes('--help') || args.includes('-h'),
            isQuietMode: args.includes('--quiet') || args.includes('-q'),
            isScriptMode: args.includes('--scripts') || args.includes('-s')
        };
    }

    /**
     * 主入口函数
     */
    async main() {
        try {
            // 处理特殊模式
            if (this.args.isVersionMode) {
                this.showVersion();
                return;
            }

            if (this.args.isHelpMode) {
                this.showHelp();
                return;
            }

            if (this.args.isConfigMode) {
                await this.runConfigWizard();
                return;
            }

            if (this.args.isScriptMode) {
                await this.generateScripts();
                return;
            }

            // 正常启动流程
            await this.startup();
            
        } catch (error) {
            console.error(chalk.red('🚨 启动失败:'), error.message);
            if (this.args.isDebugMode) {
                console.error(error.stack);
            }
            process.exit(1);
        }
    }

    /**
     * 启动流程
     */
    async startup() {
        if (!this.args.isQuietMode) {
            this.showBanner();
        }

        // 1. 环境检查
        const spinner = ora('检查运行环境...').start();
        const envResult = await this.envChecker.checkAll();
        
        if (!envResult.passed) {
            spinner.fail('环境检查失败');
            process.exit(1);
        }
        spinner.succeed('环境检查通过');

        // 2. 配置初始化
        spinner.start('初始化配置...');
        const configPaths = await this.configManager.ensureConfig();
        spinner.succeed('配置初始化完成');

        // 3. 根据模式执行
        if (this.args.isTestMode) {
            await this.runTests();
        } else {
            await this.startMCPServer(configPaths);
        }
    }

    /**
     * 显示横幅
     */
    showBanner() {
        const mode = this.args.isTestMode ? '测试模式' : 
                    this.args.isDebugMode ? 'MCP服务模式 (调试)' : 
                    'MCP服务模式';

        console.log(chalk.cyan(`
╭─────────────────────────────────────────────────────────────╮
│                🖥️  Remote Terminal MCP v0.1.0             │
│                    统一远程终端管理服务                     │
╰─────────────────────────────────────────────────────────────╯`));
        
        console.log(chalk.blue(`📋 运行模式: ${mode}`));
        
        if (this.args.isTestMode || this.args.isDebugMode) {
            console.log(chalk.gray(`📁 包目录: ${this.packageDir}`));
            console.log(chalk.gray(`⚙️  配置目录: ${this.configManager.configDir}`));
        }
        console.log('');
    }

    /**
     * 显示版本信息
     */
    showVersion() {
        const pkg = require('./package.json');
        console.log(`${pkg.name} v${pkg.version}`);
    }

    /**
     * 显示帮助信息
     */
    showHelp() {
        console.log(chalk.cyan(`
🖥️  Remote Terminal MCP - 统一远程终端管理

用法:
  npx @xuyehua/remote-terminal-mcp [选项]

选项:
  -h, --help      显示帮助信息
  -v, --version   显示版本信息
  -t, --test      运行测试模式
  -d, --debug     启用调试模式
  -c, --config    运行配置向导
  -s, --scripts   生成连接脚本
  -q, --quiet     静默模式

示例:
  # 正常启动MCP服务
  npx @xuyehua/remote-terminal-mcp
  
  # 调试模式
  npx @xuyehua/remote-terminal-mcp --debug
  
  # 测试功能
  npx @xuyehua/remote-terminal-mcp --test
  
  # 配置向导
  npx @xuyehua/remote-terminal-mcp --config
  
  # 生成连接脚本
  npx @xuyehua/remote-terminal-mcp --scripts

更多信息: https://github.com/xuyehua/remote-terminal-mcp
`));
    }

    /**
     * 运行配置向导
     */
    async runConfigWizard() {
        await this.configManager.runConfigWizard();
    }

    /**
     * 生成连接脚本
     */
    async generateScripts() {
        console.log(chalk.cyan('🛠️ 正在为所有服务器生成连接脚本...'))
        
        // 初始化配置
        await this.configManager.ensureConfig();
        
        // 生成脚本
        const success = await this.scriptGenerator.generateAllScripts();
        
        if (success) {
            console.log(chalk.green('✅ 连接脚本生成完成！'));
            
            // 显示使用说明
            this.scriptGenerator.showUsageInstructions();
            
            console.log(chalk.blue('📝 下一步:'));
            console.log('• 直接在终端中运行这些脚本');
            console.log('• 或在Cursor中使用 "connect_to_server" 工具');
        } else {
            console.log(chalk.red('❌ 脚本生成失败'));
            process.exit(1);
        }
    }

    /**
     * 启动MCP服务器
     */
    async startMCPServer(configPaths) {
        const spinner = ora('启动MCP服务器...').start();
        
        const pythonScript = path.join(this.pythonDir, 'mcp_server.py');
        
        if (!fs.existsSync(pythonScript)) {
            spinner.fail(`MCP服务器脚本不存在: ${pythonScript}`);
            process.exit(1);
        }

        spinner.succeed('MCP服务器准备就绪');

        if (this.args.isDebugMode) {
            console.log(chalk.gray(`🐍 Python脚本: ${pythonScript}`));
            console.log(chalk.gray(`📄 主配置: ${configPaths.configFile}`));
            console.log(chalk.gray(`🖥️  服务器配置: ${configPaths.serversConfigFile}`));
            console.log('');
        }

        console.log(chalk.green('✅ MCP服务器已启动，正在等待Cursor连接...'));
        
        if (!this.args.isDebugMode) {
            console.log(chalk.gray('💡 提示: 使用 --debug 参数查看详细日志'));
        }

        // 启动Python MCP服务器
        const mcp = spawn('python3', [pythonScript], {
            stdio: ['pipe', 'pipe', this.args.isDebugMode ? 'inherit' : 'pipe'],
            env: { 
                ...process.env, 
                CURSOR_BRIDGE_CONFIG: configPaths.configFile,
                CURSOR_BRIDGE_SERVERS: configPaths.serversConfigFile,
                PYTHONPATH: this.pythonDir,
                MCP_DEBUG: this.args.isDebugMode ? '1' : '0'
            }
        });

        // 转发stdio用于MCP通信
        process.stdin.pipe(mcp.stdin);
        mcp.stdout.pipe(process.stdout);

        // 处理进程事件
        mcp.on('close', (code) => {
            if (this.args.isDebugMode) {
                console.error(chalk.yellow(`📴 MCP服务器退出，代码: ${code}`));
            }
            process.exit(code);
        });

        mcp.on('error', (error) => {
            console.error(chalk.red('❌ MCP服务器错误:'), error.message);
            process.exit(1);
        });

        // 优雅退出处理
        process.on('SIGINT', () => {
            console.log(chalk.yellow('\\n🛑 正在关闭MCP服务器...'));
            mcp.kill('SIGTERM');
        });
    }

    /**
     * 运行测试
     */
    async runTests() {
        console.log(chalk.blue('🧪 运行功能测试...\\n'));

        const tests = [
            { name: 'Python脚本', test: () => this.testPythonScript() },
            { name: 'tmux命令', test: () => this.testTmux() },
            { name: '配置文件', test: () => this.testConfigFiles() },
            { name: 'MCP协议', test: () => this.testMCPProtocol() },
            { name: '脚本生成', test: () => this.testScriptGeneration() }
        ];

        let passedTests = 0;
        
        for (const { name, test } of tests) {
            const spinner = ora(`测试 ${name}...`).start();
            
            try {
                const result = await test();
                if (result) {
                    spinner.succeed(`${name} 测试通过`);
                    passedTests++;
                } else {
                    spinner.fail(`${name} 测试失败`);
                }
            } catch (error) {
                spinner.fail(`${name} 测试错误: ${error.message}`);
            }
        }

        console.log('');
        if (passedTests === tests.length) {
            console.log(chalk.green('🎉 所有测试通过！NPM包准备就绪'));
            this.showUsageInstructions();
        } else {
            console.log(chalk.red(`❌ ${tests.length - passedTests}/${tests.length} 项测试失败`));
            process.exit(1);
        }

        process.exit(0);
    }

    /**
     * 测试Python脚本
     */
    async testPythonScript() {
        const pythonScript = path.join(this.pythonDir, 'mcp_server.py');
        
        if (!fs.existsSync(pythonScript)) {
            throw new Error('Python脚本不存在');
        }

        // 测试脚本语法
        return new Promise((resolve) => {
            const process = spawn('python3', ['-m', 'py_compile', pythonScript], {
                stdio: 'pipe'
            });
            
            process.on('close', (code) => {
                resolve(code === 0);
            });
        });
    }

    /**
     * 测试tmux
     */
    async testTmux() {
        return new Promise((resolve) => {
            const process = spawn('tmux', ['-V'], { stdio: 'pipe' });
            process.on('close', (code) => resolve(code === 0));
            process.on('error', () => resolve(false));
        });
    }

    /**
     * 测试配置文件
     */
    async testConfigFiles() {
        const config = this.configManager.readConfig();
        const servers = this.configManager.readServersConfig();
        
        return config && servers && 
               config.settings && 
               servers.servers && 
               Object.keys(servers.servers).length > 0;
    }

    /**
     * 测试MCP协议
     */
    async testMCPProtocol() {
        // 简单测试：检查Python脚本是否包含必要的MCP方法
        const pythonScript = path.join(this.pythonDir, 'mcp_server.py');
        
        if (!fs.existsSync(pythonScript)) {
            return false;
        }

        const content = fs.readFileSync(pythonScript, 'utf8');
        const requiredMethods = ['handle_initialize', 'handle_list_tools', 'handle_tool_call'];
        
        return requiredMethods.every(method => content.includes(method));
    }

    /**
     * 测试脚本生成
     */
    async testScriptGeneration() {
        try {
            // 清理现有脚本
            this.scriptGenerator.cleanupScripts();
            
            // 生成脚本
            const success = await this.scriptGenerator.generateAllScripts();
            if (!success) return false;
            
            // 检查生成的脚本
            const scripts = this.scriptGenerator.listGeneratedScripts();
            
            // 再次清理（保持测试环境干净）
            this.scriptGenerator.cleanupScripts();
            
            return scripts.length > 0;
        } catch (error) {
            return false;
        }
    }

    /**
     * 显示使用说明
     */
    showUsageInstructions() {
        console.log(chalk.blue('\\n💡 使用方法:'));
        console.log('将以下配置添加到 ~/.cursor/mcp.json:');
        console.log(chalk.gray(JSON.stringify({
            "remote-terminal": {
                "command": "npx",
                "args": ["-y", "@xuyehua/remote-terminal-mcp"],
                "disabled": false,
                "autoApprove": true
            }
        }, null, 2)));
        
        console.log(chalk.blue('\\n🔧 配置管理:'));
        console.log('  • 运行配置向导: npx @xuyehua/cursor-bridge-mcp --config');
        console.log('  • 查看服务器列表: 配置文件位于 ~/.cursor-bridge/servers.yaml');
        console.log('  • 调试模式: npx @xuyehua/cursor-bridge-mcp --debug');
    }
}

// 直接执行
if (require.main === module) {
    const terminal = new RemoteTerminalMCP();
    terminal.main().catch(error => {
        console.error(chalk.red('🚨 未处理的错误:'), error);
        process.exit(1);
    });
}

module.exports = RemoteTerminalMCP;