#!/usr/bin/env node

/**
 * NPM包安装后脚本
 * 检查环境并提供使用指导
 */

const chalk = require('chalk');
const { spawn } = require('child_process');

async function postInstall() {
    console.log(chalk.cyan(`
╭─────────────────────────────────────────────────────────────╮
│          🎉 Cursor-Bridge MCP 安装成功！                   │
╰─────────────────────────────────────────────────────────────╯`));

    console.log(chalk.blue('\n🔍 正在检查环境...'));
    
    // 检查Python
    try {
        const pythonResult = await runCommand('python3', ['--version']);
        console.log(chalk.green(`✅ Python: ${pythonResult.trim()}`));
    } catch (error) {
        console.log(chalk.red('❌ Python3未安装或不在PATH中'));
        console.log(chalk.yellow('   请安装Python 3.8+: https://python.org'));
    }

    // 检查tmux
    try {
        const tmuxResult = await runCommand('tmux', ['-V']);
        console.log(chalk.green(`✅ tmux: ${tmuxResult.trim()}`));
    } catch (error) {
        console.log(chalk.yellow('⚠️  tmux未安装 (某些功能受限)'));
        console.log(chalk.gray('   安装tmux: brew install tmux (macOS) 或 apt install tmux (Ubuntu)'));
    }

    console.log(chalk.blue('\n📋 下一步操作:'));
    console.log('1. 将以下配置添加到 ~/.cursor/mcp.json:');
    console.log(chalk.gray(`
{
  "mcpServers": {
    "cursor-bridge": {
      "command": "npx",
      "args": ["-y", "@xuyehua/cursor-bridge-mcp"],
      "disabled": false,
      "autoApprove": true
    }
  }
}`));

    console.log('\n2. 重启Cursor编辑器');
    console.log('\n3. 在Cursor中测试: "列出所有服务器"');

    console.log(chalk.blue('\n🛠️ 可用命令:'));
    console.log('• 测试功能: npx @xuyehua/cursor-bridge-mcp --test');
    console.log('• 配置向导: npx @xuyehua/cursor-bridge-mcp --config');
    console.log('• 调试模式: npx @xuyehua/cursor-bridge-mcp --debug');
    console.log('• 查看帮助: npx @xuyehua/cursor-bridge-mcp --help');

    console.log(chalk.green('\n🌟 享受使用Cursor-Bridge MCP！'));
    console.log(chalk.gray('   文档: https://github.com/xuyehua/cursor-bridge-mcp'));
}

function runCommand(command, args) {
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
                resolve(output || error);
            } else {
                reject(new Error(`Command failed: ${error}`));
            }
        });

        process.on('error', reject);
    });
}

if (require.main === module) {
    postInstall().catch(console.error);
}

module.exports = postInstall;