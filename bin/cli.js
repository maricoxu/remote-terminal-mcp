#!/usr/bin/env node

const path = require('path');
const os = require('os');
const fs = require('fs');

function runDiagnostics() {
    const reportPath = path.join(os.homedir(), 'diagnostic_report.log');
    let reportContent = `--- Diagnostic Report (v0.4.16) ---\n`;
    reportContent += `Timestamp: ${new Date().toISOString()}\n\n`;
    
    // 1. CWD
    try {
        reportContent += `process.cwd(): ${process.cwd()}\n`;
    } catch (e) {
        reportContent += `Failed to get process.cwd(): ${e.message}\n`;
    }
    
    // 2. Home Directory
    try {
        reportContent += `os.homedir(): ${os.homedir()}\n`;
    } catch (e) {
        reportContent += `Failed to get os.homedir(): ${e.message}\n`;
    }

    // 3. __dirname
    try {
        reportContent += `__dirname: ${__dirname}\n`;
    } catch (e) {
        reportContent += `Failed to get __dirname: ${e.message}\n`;
    }
    
    // 4. Environment Variables
    reportContent += `\n--- Environment Variables ---\n`;
    reportContent += JSON.stringify(process.env, null, 2);
    reportContent += `\n\n--- End of Report ---\n`;
    
    try {
        fs.writeFileSync(reportPath, reportContent);
    } catch(e) {
        // If this fails, there's nothing more we can do.
    }
}

// Run the diagnostics and then exit. Do not start the server.
runDiagnostics();
process.exit(0); 