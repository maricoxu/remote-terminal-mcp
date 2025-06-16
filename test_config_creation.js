const fs = require('fs');
const path = require('path');
const os = require('os');

const configDir = path.join(os.homedir(), '.remote-terminal');
const userConfig = path.join(configDir, 'config.yaml');

console.log('Config dir:', configDir);
console.log('User config:', userConfig);
console.log('Dir exists:', fs.existsSync(configDir));

if (!fs.existsSync(configDir)) {
  fs.mkdirSync(configDir, { recursive: true });
  console.log('Created directory');
}

const testContent = `# Test configuration
servers:
  test-server:
    host: test.com
    port: 22
`;

try {
  fs.writeFileSync(userConfig, testContent, 'utf8');
  console.log('File written successfully');
  console.log('File exists after write:', fs.existsSync(userConfig));
  
  if (fs.existsSync(userConfig)) {
    console.log('File content:');
    console.log(fs.readFileSync(userConfig, 'utf8'));
  }
} catch (error) {
  console.error('Error writing file:', error);
} 