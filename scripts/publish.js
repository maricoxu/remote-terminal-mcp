#!/usr/bin/env node

/**
 * NPM包发布脚本
 * 自动化版本管理和发布流程
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const chalk = require('chalk');

// 日志函数
const log = {
    info: (msg) => console.log(chalk.blue('ℹ'), msg),
    success: (msg) => console.log(chalk.green('✅'), msg),
    warning: (msg) => console.log(chalk.yellow('⚠️'), msg),
    error: (msg) => console.log(chalk.red('❌'), msg),
    step: (msg) => console.log(chalk.cyan('🔄'), msg)
};

// 执行命令
function runCommand(command, description) {
    log.step(description);
    try {
        const result = execSync(command, { encoding: 'utf8', stdio: 'pipe' });
        log.success(`${description} - 完成`);
        return result;
    } catch (error) {
        log.error(`${description} - 失败: ${error.message}`);
        throw error;
    }
}

// 检查文件是否存在
function checkFile(filePath, description) {
    if (fs.existsSync(filePath)) {
        log.success(`${description} - 存在`);
        return true;
    } else {
        log.error(`${description} - 不存在: ${filePath}`);
        return false;
    }
}

// 主发布流程
async function publishPackage() {
    log.info('开始NPM包发布流程...');
    
    try {
        // 1. 检查必要文件
        log.step('检查必要文件...');
        const requiredFiles = [
            { path: 'package.json', desc: 'package.json' },
            { path: 'README.md', desc: 'README.md' },
            { path: 'LICENSE', desc: 'LICENSE' },
            { path: 'index.js', desc: '主入口文件' },
            { path: 'bin/remote-terminal-mcp', desc: '可执行文件' },
            { path: 'python/mcp_server.py', desc: 'Python MCP服务器' },
            { path: 'docker_config_manager.py', desc: 'Docker配置管理器' },
            { path: 'enhanced_config_manager.py', desc: '增强配置管理器' }
        ];
        
        let allFilesExist = true;
        for (const file of requiredFiles) {
            if (!checkFile(file.path, file.desc)) {
                allFilesExist = false;
            }
        }
        
        if (!allFilesExist) {
            throw new Error('缺少必要文件，无法发布');
        }
        
        // 2. 检查package.json
        log.step('验证package.json...');
        const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
        log.info(`包名: ${packageJson.name}`);
        log.info(`版本: ${packageJson.version}`);
        log.info(`描述: ${packageJson.description}`);
        
        // 3. 检查Git状态
        log.step('检查Git状态...');
        try {
            const gitStatus = runCommand('git status --porcelain', '检查Git工作区状态');
            if (gitStatus.trim()) {
                log.warning('工作区有未提交的更改:');
                console.log(gitStatus);
                
                // 询问是否继续
                const readline = require('readline');
                const rl = readline.createInterface({
                    input: process.stdin,
                    output: process.stdout
                });
                
                const answer = await new Promise((resolve) => {
                    rl.question('是否继续发布? (y/N): ', resolve);
                });
                rl.close();
                
                if (answer.toLowerCase() !== 'y') {
                    log.info('发布已取消');
                    return;
                }
            }
        } catch (error) {
            log.warning('无法检查Git状态，可能不在Git仓库中');
        }
        
        // 4. 运行测试
        log.step('运行测试...');
        try {
            runCommand('npm test', '运行测试套件');
        } catch (error) {
            log.warning('测试失败，但继续发布流程');
        }
        
        // 5. 构建包
        log.step('构建NPM包...');
        runCommand('npm pack', '创建NPM包');
        
        // 6. 检查包内容
        log.step('检查包内容...');
        const tarballName = `${packageJson.name.replace('@', '').replace('/', '-')}-${packageJson.version}.tgz`;
        if (fs.existsSync(tarballName)) {
            log.success(`包文件已创建: ${tarballName}`);
            
            // 显示包大小
            const stats = fs.statSync(tarballName);
            const sizeInMB = (stats.size / (1024 * 1024)).toFixed(2);
            log.info(`包大小: ${sizeInMB} MB`);
        }
        
        // 7. 发布到NPM
        log.step('发布到NPM...');
        
        // 检查是否已登录NPM
        try {
            const whoami = runCommand('npm whoami', '检查NPM登录状态');
            log.info(`当前NPM用户: ${whoami.trim()}`);
        } catch (error) {
            log.error('未登录NPM，请先运行: npm login');
            return;
        }
        
        // 发布包
        try {
            runCommand('npm publish --access public', '发布包到NPM');
            log.success(`🎉 包 ${packageJson.name}@${packageJson.version} 发布成功！`);
        } catch (error) {
            if (error.message.includes('already exists')) {
                log.warning('该版本已存在，请更新版本号后重试');
            } else {
                throw error;
            }
        }
        
        // 8. 清理临时文件
        log.step('清理临时文件...');
        if (fs.existsSync(tarballName)) {
            fs.unlinkSync(tarballName);
            log.success('临时文件已清理');
        }
        
        // 9. 创建Git标签（如果在Git仓库中）
        try {
            const tagName = `v${packageJson.version}`;
            runCommand(`git tag ${tagName}`, `创建Git标签 ${tagName}`);
            runCommand(`git push origin ${tagName}`, '推送标签到远程仓库');
            log.success(`Git标签 ${tagName} 已创建并推送`);
        } catch (error) {
            log.warning('无法创建Git标签，可能不在Git仓库中或标签已存在');
        }
        
        log.success('🎉 发布流程完成！');
        log.info(`安装命令: npm install ${packageJson.name}`);
        log.info(`使用命令: npx ${packageJson.name.split('/').pop()}`);
        
    } catch (error) {
        log.error(`发布失败: ${error.message}`);
        process.exit(1);
    }
}

// 版本管理函数
function updateVersion(type = 'patch') {
    log.step(`更新版本 (${type})...`);
    try {
        const result = runCommand(`npm version ${type} --no-git-tag-version`, `版本更新为 ${type}`);
        const newVersion = result.trim().replace('v', '');
        log.success(`版本已更新为: ${newVersion}`);
        return newVersion;
    } catch (error) {
        log.error(`版本更新失败: ${error.message}`);
        throw error;
    }
}

// 命令行参数处理
const args = process.argv.slice(2);
const command = args[0];

switch (command) {
    case 'patch':
    case 'minor':
    case 'major':
        updateVersion(command);
        break;
    case 'publish':
        publishPackage();
        break;
    case 'version-and-publish':
        const versionType = args[1] || 'patch';
        updateVersion(versionType);
        publishPackage();
        break;
    default:
        console.log(`
使用方法:
  node scripts/publish.js patch          # 更新补丁版本
  node scripts/publish.js minor          # 更新次要版本  
  node scripts/publish.js major          # 更新主要版本
  node scripts/publish.js publish        # 发布当前版本
  node scripts/publish.js version-and-publish [patch|minor|major]  # 更新版本并发布
        `);
        break;
}