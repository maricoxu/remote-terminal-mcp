const fs = require('fs');
const path = require('path');
const os = require('os');
const chalk = require('chalk');

/**
 * 脚本生成器 - 为服务器生成连接脚本
 */
class ScriptGenerator {
    constructor(configManager) {
        this.configManager = configManager;
        this.templatePath = path.join(__dirname, '..', 'templates', 'connection-script-template.sh');
        this.outputDir = path.join(os.homedir(), '.cursor-bridge', 'scripts');
    }

    /**
     * 为所有服务器生成连接脚本
     */
    async generateAllScripts() {
        const servers = this.configManager.listServers();
        
        if (servers.length === 0) {
            console.log(chalk.yellow('❌ 没有找到服务器配置'));
            return false;
        }

        // 确保输出目录存在
        if (!fs.existsSync(this.outputDir)) {
            fs.mkdirSync(this.outputDir, { recursive: true });
            console.log(chalk.blue(`📁 创建脚本目录: ${this.outputDir}`));
        }

        let successCount = 0;
        
        for (const server of servers) {
            try {
                await this.generateScript(server);
                successCount++;
            } catch (error) {
                console.log(chalk.red(`❌ 生成脚本失败 (${server.id}): ${error.message}`));
            }
        }

        console.log(chalk.green(`✅ 成功生成 ${successCount}/${servers.length} 个连接脚本`));
        console.log(chalk.gray(`📁 脚本位置: ${this.outputDir}`));
        
        return successCount > 0;
    }

    /**
     * 为特定服务器生成连接脚本
     */
    async generateScript(server, sessionName = 'default') {
        if (!fs.existsSync(this.templatePath)) {
            throw new Error(`模板文件不存在: ${this.templatePath}`);
        }

        // 读取模板
        const template = fs.readFileSync(this.templatePath, 'utf8');
        
        // 替换变量
        const script = this.replaceTemplateVariables(template, server, sessionName);
        
        // 生成脚本文件名
        const scriptName = `connect_${server.id}.sh`;
        const scriptPath = path.join(this.outputDir, scriptName);
        
        // 写入脚本文件
        fs.writeFileSync(scriptPath, script);
        
        // 设置执行权限
        fs.chmodSync(scriptPath, 0o755);
        
        console.log(chalk.green(`✅ 生成脚本: ${scriptName}`));
        
        return scriptPath;
    }

    /**
     * 替换模板变量
     */
    replaceTemplateVariables(template, server, sessionName) {
        const replacements = {
            '{{SERVER_ID}}': server.id || 'unknown',
            '{{SERVER_NAME}}': server.name || server.id,
            '{{SERVER_HOST}}': server.host || 'localhost',
            '{{JUMP_HOST}}': server.jump_host || '',
            '{{CONTAINER_NAME}}': server.container_name || 'xyh_pytorch',
            '{{SESSION_NAME}}': sessionName || 'default'
        };

        let result = template;
        for (const [placeholder, value] of Object.entries(replacements)) {
            result = result.replace(new RegExp(placeholder, 'g'), value);
        }

        return result;
    }

    /**
     * 获取特定服务器的脚本路径
     */
    getScriptPath(serverId) {
        const scriptName = `connect_${serverId}.sh`;
        return path.join(this.outputDir, scriptName);
    }

    /**
     * 检查脚本是否存在
     */
    scriptExists(serverId) {
        const scriptPath = this.getScriptPath(serverId);
        return fs.existsSync(scriptPath);
    }

    /**
     * 列出所有生成的脚本
     */
    listGeneratedScripts() {
        if (!fs.existsSync(this.outputDir)) {
            return [];
        }

        const files = fs.readdirSync(this.outputDir);
        return files
            .filter(file => file.startsWith('connect_') && file.endsWith('.sh'))
            .map(file => {
                const serverId = file.replace('connect_', '').replace('.sh', '');
                const scriptPath = path.join(this.outputDir, file);
                const stats = fs.statSync(scriptPath);
                
                return {
                    serverId,
                    fileName: file,
                    path: scriptPath,
                    size: stats.size,
                    modified: stats.mtime
                };
            });
    }

    /**
     * 显示脚本使用说明
     */
    showUsageInstructions() {
        const scripts = this.listGeneratedScripts();
        
        if (scripts.length === 0) {
            console.log(chalk.yellow('❌ 没有找到生成的脚本'));
            return;
        }

        console.log(chalk.blue('\\n🚀 连接脚本使用说明:\\n'));
        
        scripts.forEach(script => {
            const server = this.configManager.getServerConfig(script.serverId);
            const serverName = server ? server.name : script.serverId;
            
            console.log(chalk.green(`📋 ${serverName} (${script.serverId})`));
            console.log(chalk.gray(`   脚本: ${script.path}`));
            console.log(chalk.gray('   用法:'));
            console.log(chalk.gray(`     ${script.path} connect    # SSH连接`));
            console.log(chalk.gray(`     ${script.path} docker     # Docker环境`));
            console.log(chalk.gray(`     ${script.path} tmux       # tmux会话`));
            console.log(chalk.gray(`     ${script.path} full       # 完整流程`));
            console.log('');
        });

        console.log(chalk.blue('💡 提示:'));
        console.log('  • 脚本支持多种连接模式');
        console.log('  • 使用 full 模式获得最佳体验');
        console.log('  • 可以直接在终端中执行这些脚本');
    }

    /**
     * 更新所有脚本
     */
    async updateAllScripts() {
        console.log(chalk.blue('🔄 更新所有连接脚本...'));
        
        // 删除旧脚本
        if (fs.existsSync(this.outputDir)) {
            const oldScripts = fs.readdirSync(this.outputDir)
                .filter(file => file.startsWith('connect_') && file.endsWith('.sh'));
            
            oldScripts.forEach(script => {
                fs.unlinkSync(path.join(this.outputDir, script));
            });
            
            console.log(chalk.gray(`🗑️  删除了 ${oldScripts.length} 个旧脚本`));
        }
        
        // 生成新脚本
        return await this.generateAllScripts();
    }

    /**
     * 清理所有脚本
     */
    cleanupScripts() {
        if (!fs.existsSync(this.outputDir)) {
            console.log(chalk.yellow('❌ 脚本目录不存在'));
            return false;
        }

        const scripts = fs.readdirSync(this.outputDir)
            .filter(file => file.startsWith('connect_') && file.endsWith('.sh'));

        scripts.forEach(script => {
            fs.unlinkSync(path.join(this.outputDir, script));
        });

        console.log(chalk.green(`🗑️  清理了 ${scripts.length} 个脚本`));
        return true;
    }
}

module.exports = ScriptGenerator;