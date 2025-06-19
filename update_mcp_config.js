#!/usr/bin/env node

/**
 * 更新Cursor MCP配置脚本
 * 添加本地版本，暂时禁用NPM版本
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const MCP_CONFIG_PATH = path.join(os.homedir(), '.cursor', 'mcp.json');
const PROJECT_ROOT = __dirname;

console.log('🔧 更新Cursor MCP配置');
console.log('===================');

function updateMCPConfig() {
    try {
        // 读取当前配置
        if (!fs.existsSync(MCP_CONFIG_PATH)) {
            console.error(`❌ MCP配置文件不存在: ${MCP_CONFIG_PATH}`);
            return;
        }

        const config = JSON.parse(fs.readFileSync(MCP_CONFIG_PATH, 'utf8'));
        
        console.log(`📁 项目路径: ${PROJECT_ROOT}`);
        console.log(`📄 MCP配置路径: ${MCP_CONFIG_PATH}`);

        // 备份当前配置
        const backupPath = `${MCP_CONFIG_PATH}.backup.${new Date().toISOString().replace(/[:.]/g, '-')}`;
        fs.writeFileSync(backupPath, JSON.stringify(config, null, 2));
        console.log(`💾 已备份当前配置到: ${backupPath}`);

        // 添加本地版本
        config.mcpServers['remote-terminal-mcp-local'] = {
            "command": "node",
            "args": [path.join(PROJECT_ROOT, "index.js")],
            "env": {
                "MCP_DEBUG": "1",
                "PYTHONPATH": PROJECT_ROOT,
                "MCP_LOCAL_MODE": "true"
            }
        };

        // 禁用NPM版本（暂时）
        if (config.mcpServers['remote-terminal-mcp']) {
            config.mcpServers['remote-terminal-mcp'].disabled = true;
            console.log('⏸️  已禁用NPM版本的remote-terminal-mcp');
        }

        // 写入更新后的配置
        fs.writeFileSync(MCP_CONFIG_PATH, JSON.stringify(config, null, 2));
        
        console.log('✅ MCP配置已更新');
        console.log('\n📋 新增的本地配置:');
        console.log(JSON.stringify({
            'remote-terminal-mcp-local': config.mcpServers['remote-terminal-mcp-local']
        }, null, 2));
        
        console.log('\n🔄 请重启Cursor以加载新的MCP配置');
        
    } catch (error) {
        console.error(`❌ 更新配置失败: ${error.message}`);
        process.exit(1);
    }
}

function restoreNpmVersion() {
    try {
        const config = JSON.parse(fs.readFileSync(MCP_CONFIG_PATH, 'utf8'));
        
        // 启用NPM版本
        if (config.mcpServers['remote-terminal-mcp']) {
            delete config.mcpServers['remote-terminal-mcp'].disabled;
            console.log('▶️  已启用NPM版本的remote-terminal-mcp');
        }
        
        // 删除本地版本
        if (config.mcpServers['remote-terminal-mcp-local']) {
            delete config.mcpServers['remote-terminal-mcp-local'];
            console.log('🗑️  已删除本地版本的remote-terminal-mcp-local');
        }
        
        fs.writeFileSync(MCP_CONFIG_PATH, JSON.stringify(config, null, 2));
        console.log('✅ 已恢复到NPM版本');
        
    } catch (error) {
        console.error(`❌ 恢复配置失败: ${error.message}`);
        process.exit(1);
    }
}

// 处理命令行参数
const command = process.argv[2];

switch (command) {
    case 'add-local':
        updateMCPConfig();
        break;
    case 'restore-npm':
        restoreNpmVersion();
        break;
    case 'status':
        try {
            const config = JSON.parse(fs.readFileSync(MCP_CONFIG_PATH, 'utf8'));
            console.log('📋 当前MCP服务器状态:');
            
            if (config.mcpServers['remote-terminal-mcp-local']) {
                console.log('  ✅ 本地版本: 已配置');
            } else {
                console.log('  ❌ 本地版本: 未配置');
            }
            
            if (config.mcpServers['remote-terminal-mcp']) {
                const disabled = config.mcpServers['remote-terminal-mcp'].disabled;
                console.log(`  ${disabled ? '⏸️' : '✅'} NPM版本: ${disabled ? '已禁用' : '已启用'}`);
            } else {
                console.log('  ❌ NPM版本: 未配置');
            }
        } catch (error) {
            console.error(`❌ 读取配置失败: ${error.message}`);
        }
        break;
    default:
        console.log('用法:');
        console.log('  node update_mcp_config.js add-local     - 添加本地版本并禁用NPM版本');
        console.log('  node update_mcp_config.js restore-npm   - 恢复NPM版本并删除本地版本');
        console.log('  node update_mcp_config.js status        - 显示当前状态');
        break;
} 