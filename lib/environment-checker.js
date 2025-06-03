const { spawn } = require('child_process');
const chalk = require('chalk');

/**
 * 环境检查器 - 验证运行环境
 */
class EnvironmentChecker {
    constructor() {
        this.requirements = {
            python: { min: '3.8.0', command: 'python3 --version' },
            tmux: { min: '2.0', command: 'tmux -V' },
            node: { min: '14.0.0', command: 'node --version' }
        };
    }

    /**
     * 检查所有环境要求
     */
    async checkAll() {
        console.log(chalk.blue('🔍 检查运行环境...'));
        
        const results = {};
        let allPassed = true;

        // 检查Python
        results.python = await this.checkPython();
        if (!results.python.passed) allPassed = false;

        // 检查tmux
        results.tmux = await this.checkTmux();
        if (!results.tmux.passed) allPassed = false;

        // 检查Node.js
        results.node = await this.checkNode();
        if (!results.node.passed) allPassed = false;

        // 总结
        if (allPassed) {
            console.log(chalk.green('✅ 所有环境检查通过'));
        } else {
            console.log(chalk.red('❌ 某些环境检查失败'));
            this.printFailureHelp(results);
        }

        return { passed: allPassed, details: results };
    }

    /**
     * 检查Python环境
     */
    async checkPython() {
        try {
            const version = await this.getVersion('python3', ['--version']);
            const versionNumber = this.extractVersion(version);
            const passed = this.compareVersions(versionNumber, this.requirements.python.min);
            
            if (passed) {
                console.log(chalk.green(`✅ Python: ${version.trim()}`));
            } else {
                console.log(chalk.red(`❌ Python: ${version.trim()} (需要 >= ${this.requirements.python.min})`));
            }

            return { passed, version: versionNumber, output: version };
        } catch (error) {
            console.log(chalk.red('❌ Python: 未安装或不在PATH中'));
            return { passed: false, error: error.message };
        }
    }

    /**
     * 检查tmux
     */
    async checkTmux() {
        try {
            const version = await this.getVersion('tmux', ['-V']);
            const versionNumber = this.extractVersion(version);
            const passed = this.compareVersions(versionNumber, this.requirements.tmux.min);
            
            if (passed) {
                console.log(chalk.green(`✅ tmux: ${version.trim()}`));
            } else {
                console.log(chalk.red(`❌ tmux: ${version.trim()} (需要 >= ${this.requirements.tmux.min})`));
            }

            // tmux是可选的，即使版本不够也让它通过
            return { passed: true, version: versionNumber, output: version, optional: !passed };
        } catch (error) {
            console.log(chalk.yellow('⚠️  tmux: 未安装 (某些功能将受限)'));
            return { passed: true, error: error.message, optional: true };
        }
    }

    /**
     * 检查Node.js
     */
    async checkNode() {
        try {
            const version = await this.getVersion('node', ['--version']);
            const versionNumber = this.extractVersion(version);
            const passed = this.compareVersions(versionNumber, this.requirements.node.min);
            
            if (passed) {
                console.log(chalk.green(`✅ Node.js: ${version.trim()}`));
            } else {
                console.log(chalk.red(`❌ Node.js: ${version.trim()} (需要 >= ${this.requirements.node.min})`));
            }

            return { passed, version: versionNumber, output: version };
        } catch (error) {
            console.log(chalk.red('❌ Node.js: 检查失败'));
            return { passed: false, error: error.message };
        }
    }

    /**
     * 获取命令版本
     */
    getVersion(command, args) {
        return new Promise((resolve, reject) => {
            const process = spawn(command, args, { stdio: 'pipe' });
            let output = '';
            let error = '';

            process.stdout.on('data', (data) => {
                output += data.toString();
            });

            process.stderr.on('data', (data) => {
                error += data.toString();
            });

            process.on('close', (code) => {
                if (code === 0) {
                    resolve(output || error); // 有些命令输出到stderr
                } else {
                    reject(new Error(`Command failed with code ${code}: ${error}`));
                }
            });

            process.on('error', (err) => {
                reject(err);
            });
        });
    }

    /**
     * 从版本字符串中提取版本号
     */
    extractVersion(versionString) {
        const match = versionString.match(/(\d+\.\d+\.\d+)/);
        return match ? match[1] : '0.0.0';
    }

    /**
     * 比较版本号
     */
    compareVersions(version1, version2) {
        const v1 = version1.split('.').map(Number);
        const v2 = version2.split('.').map(Number);

        for (let i = 0; i < Math.max(v1.length, v2.length); i++) {
            const num1 = v1[i] || 0;
            const num2 = v2[i] || 0;

            if (num1 > num2) return true;
            if (num1 < num2) return false;
        }

        return true; // 相等也算通过
    }

    /**
     * 打印失败帮助信息
     */
    printFailureHelp(results) {
        console.log(chalk.yellow('\n💡 环境问题解决建议:'));

        if (!results.python.passed) {
            console.log(chalk.yellow('  Python:'));
            console.log('    • macOS: brew install python@3.11');
            console.log('    • Ubuntu: sudo apt install python3');
            console.log('    • 确保python3在PATH中');
        }

        if (!results.tmux.passed && !results.tmux.optional) {
            console.log(chalk.yellow('  tmux:'));
            console.log('    • macOS: brew install tmux');
            console.log('    • Ubuntu: sudo apt install tmux');
        }

        if (!results.node.passed) {
            console.log(chalk.yellow('  Node.js:'));
            console.log('    • 访问 https://nodejs.org 下载');
            console.log('    • 或使用 nvm 管理版本');
        }
    }

    /**
     * 快速检查关键环境
     */
    async quickCheck() {
        const pythonOk = await this.checkPython();
        return pythonOk.passed;
    }
}

module.exports = EnvironmentChecker;