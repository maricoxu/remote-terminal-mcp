#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

// This script is executed after the package is installed.
// Its purpose is to programmatically ensure that our CLI entry point
// has the necessary execute permissions and manage configuration files safely.

const cliScriptPath = path.join(__dirname, '..', 'bin', 'cli.js');

try {
  // Set permissions to rwxr-xr-x (755)
  fs.chmodSync(cliScriptPath, 0o755);
  // We don't log on success to keep installation clean,
  // but you could add a console.log here for debugging.
} catch (error) {
  // If we fail, log the error clearly. This is critical for debugging.
  console.error(
    `[postinstall.js] FATAL: Failed to set execute permission on ${cliScriptPath}`
  );
  console.error(error);
  // Exit with a non-zero code to indicate failure.
  process.exit(1);
}

// Smart configuration management - only create default config if user doesn't have one
function initializeUserConfig() {
  const userConfigDir = path.join(os.homedir(), '.remote-terminal-mcp');
  const userConfigFile = path.join(userConfigDir, 'config.yaml');
  
  // Check if user already has a config file
  if (fs.existsSync(userConfigFile)) {
    // User has existing config, don't touch it
    return;
  }
  
  // Create user config directory if it doesn't exist
  if (!fs.existsSync(userConfigDir)) {
    try {
      fs.mkdirSync(userConfigDir, { recursive: true });
    } catch (error) {
      // Silently fail if we can't create directory
      return;
    }
  }
  
  // Create a minimal default config only if user doesn't have one
  const defaultConfig = `# Remote Terminal MCP Configuration
# This file was automatically created. You can customize it as needed.
# For full configuration examples, see: https://github.com/maricoxu/remote-terminal-mcp

servers: {}

# Use the interactive configuration manager to add servers:
# python3 enhanced_config_manager.py
`;
  
  try {
    fs.writeFileSync(userConfigFile, defaultConfig, 'utf8');
  } catch (error) {
    // Silently fail if we can't write config
    return;
  }
}

// Initialize user config safely
try {
  initializeUserConfig();
} catch (error) {
  // Don't fail installation if config initialization fails
} 