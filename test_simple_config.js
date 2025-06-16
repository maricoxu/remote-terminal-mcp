const fs = require('fs');
const path = require('path');
const os = require('os');

console.log('=== Simple Config Test ===');

const homeDir = os.homedir();
const configDir = path.join(homeDir, '.remote-terminal');
const userConfig = path.join(configDir, 'config.yaml');

console.log(`Config directory: ${configDir}`);
console.log(`Config file: ${userConfig}`);

// Create directory
if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
    console.log('Directory created');
}

// Create config file
const configContent = `# Remote Terminal MCP Configuration
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

fs.writeFileSync(userConfig, configContent, 'utf8');
console.log('Config file written');

// Verify
if (fs.existsSync(userConfig)) {
    console.log('✅ Config file exists');
    console.log(`File size: ${fs.statSync(userConfig).size} bytes`);
} else {
    console.log('❌ Config file does not exist');
}

console.log('=== Test Complete ==='); 