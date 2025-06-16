const fs = require('fs');
const path = require('path');
const os = require('os');

const homeDir = os.homedir();
const configDir = path.join(homeDir, '.remote-terminal');

console.log(`Monitoring directory: ${configDir}`);

// Create directory if it doesn't exist
if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
    console.log('Directory created');
}

// Monitor the directory
const watcher = fs.watch(configDir, { recursive: true }, (eventType, filename) => {
    console.log(`[${new Date().toISOString()}] Event: ${eventType}, File: ${filename}`);
    
    // List directory contents
    try {
        const files = fs.readdirSync(configDir);
        console.log(`  Current files: ${files.join(', ')}`);
    } catch (error) {
        console.log(`  Error reading directory: ${error.message}`);
    }
});

console.log('Watching for changes... Press Ctrl+C to stop');

// Create config file after a short delay
setTimeout(() => {
    console.log('Creating config file...');
    const configFile = path.join(configDir, 'config.yaml');
    const content = `# Test config\ntest: true\n`;
    fs.writeFileSync(configFile, content, 'utf8');
    console.log('Config file created');
}, 1000);

// Keep the script running
process.on('SIGINT', () => {
    console.log('\nStopping monitor...');
    watcher.close();
    process.exit(0);
}); 