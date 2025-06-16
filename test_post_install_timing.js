const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

const homeDir = os.homedir();
const configDir = path.join(homeDir, '.remote-terminal');

console.log('=== Post-Install Timing Test ===');

// 删除现有目录
if (fs.existsSync(configDir)) {
    execSync(`rm -rf "${configDir}"`);
    console.log('Removed existing config directory');
}

// 运行 post-install 脚本
console.log('Running post-install script...');
try {
    execSync('node scripts/post-install.js', { stdio: 'inherit' });
    console.log('Post-install script completed');
} catch (error) {
    console.error('Post-install script failed:', error.message);
    process.exit(1);
}

// 立即检查文件状态
console.log('\n=== Immediate Check ===');
if (fs.existsSync(configDir)) {
    const files = fs.readdirSync(configDir);
    console.log(`Directory exists with ${files.length} files:`, files);
    
    const configFile = path.join(configDir, 'config.yaml');
    const markerFile = path.join(configDir, '.npm-installed');
    
    console.log(`config.yaml exists: ${fs.existsSync(configFile)}`);
    console.log(`marker file exists: ${fs.existsSync(markerFile)}`);
} else {
    console.log('Directory does not exist');
}

// 等待并再次检查
console.log('\n=== Check after 2 seconds ===');
setTimeout(() => {
    if (fs.existsSync(configDir)) {
        const files = fs.readdirSync(configDir);
        console.log(`Directory exists with ${files.length} files:`, files);
        
        const configFile = path.join(configDir, 'config.yaml');
        const markerFile = path.join(configDir, '.npm-installed');
        
        console.log(`config.yaml exists: ${fs.existsSync(configFile)}`);
        console.log(`marker file exists: ${fs.existsSync(markerFile)}`);
    } else {
        console.log('Directory does not exist');
    }
    
    console.log('\n=== Check after 5 seconds ===');
    setTimeout(() => {
        if (fs.existsSync(configDir)) {
            const files = fs.readdirSync(configDir);
            console.log(`Directory exists with ${files.length} files:`, files);
            
            const configFile = path.join(configDir, 'config.yaml');
            const markerFile = path.join(configDir, '.npm-installed');
            
            console.log(`config.yaml exists: ${fs.existsSync(configFile)}`);
            console.log(`marker file exists: ${fs.existsSync(markerFile)}`);
        } else {
            console.log('Directory does not exist');
        }
        
        console.log('\n=== Test Complete ===');
    }, 3000);
}, 2000); 