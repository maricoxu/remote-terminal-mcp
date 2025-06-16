const fs = require('fs');
const path = require('path');
const os = require('os');

// 获取包安装目录
const packageRoot = path.resolve(__dirname);
const templatesDir = path.join(packageRoot, 'templates');

console.log('Testing config file creation...');

const homeDir = os.homedir();
const configDir = path.join(homeDir, '.remote-terminal');

console.log(`Config directory: ${configDir}`);

if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
    console.log(`Configuration directory created: ${configDir}`);
}

// Copy YAML configuration template if config.yaml doesn't exist
const configTemplate = path.join(packageRoot, 'templates', 'config.yaml.template');
const userConfig = path.join(configDir, 'config.yaml');

console.log(`Template path: ${configTemplate}`);
console.log(`User config path: ${userConfig}`);
console.log(`Template exists: ${fs.existsSync(configTemplate)}`);
console.log(`User config exists: ${fs.existsSync(userConfig)}`);

if (!fs.existsSync(userConfig)) {
    if (fs.existsSync(configTemplate)) {
        // Read template and replace timestamp
        let templateContent = fs.readFileSync(configTemplate, 'utf8');
        templateContent = templateContent.replace('{{ timestamp }}', new Date().toISOString());
        
        // Write to user config
        fs.writeFileSync(userConfig, templateContent, 'utf8');
        console.log(`Configuration template created: ${userConfig}`);
        console.log('Please edit the config.yaml file to add your server details');
    } else {
        console.log('Configuration template not found, creating basic config');
        // Create a basic config if template is missing
        const basicConfig = `# Remote Terminal MCP Configuration
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
        fs.writeFileSync(userConfig, basicConfig, 'utf8');
        console.log(`Basic configuration created: ${userConfig}`);
    }
} else {
    console.log(`Configuration file already exists: ${userConfig}`);
}

console.log('Test completed!'); 