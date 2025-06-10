const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

// Since the test methods were removed from the main class, we recreate them here
// for the sole purpose of testing.

async function testPythonScript() {
    const pythonScript = path.join(__dirname, 'python', 'mcp_server.py');
    if (!fs.existsSync(pythonScript)) throw new Error('Python script does not exist');
    return new Promise((resolve) => {
        const process = spawn('python3', ['-m', 'py_compile', pythonScript], { stdio: 'pipe' });
        process.on('close', (code) => {
            console.log(`Python compile test exited with code ${code}`);
            resolve(code === 0);
        });
    });
}

async function testMCPProtocol() {
    const pythonScript = path.join(__dirname, 'python', 'mcp_server.py');
    if (!fs.existsSync(pythonScript)) return false;
    const content = fs.readFileSync(pythonScript, 'utf8');
    const requiredElements = ['handle_request', 'initialize', 'tools/list'];
    const allFound = requiredElements.every(element => content.includes(element));
    if (!allFound) {
        console.error('MCP protocol test failed. Missing elements in python script.');
    }
    return allFound;
}

async function runTests() {
    console.log('🧪 Running tests...\\n');
    
    const tests = [
        { name: 'Python script syntax', test: testPythonScript },
        { name: 'MCP protocol implementation', test: testMCPProtocol }
    ];

    let passedCount = 0;
    for (const { name, test } of tests) {
        try {
            if (await test()) {
                console.log(`✔ ${name} test passed`);
                passedCount++;
            } else {
                console.log(`✖ ${name} test failed`);
            }
        } catch (error) {
            console.log(`✖ ${name} test error: ${error.message}`);
        }
    }

    console.log('');
    if (passedCount !== tests.length) {
        console.log(`❌ ${tests.length - passedCount}/${tests.length} tests failed`);
        throw new Error('Some tests failed.');
    } else {
        console.log('🎉 All tests passed!');
    }
}


async function run() {
    console.log('🚀 Starting dedicated test runner...');
    try {
        await runTests();
        console.log('✅ Test runner finished successfully.');
        process.exit(0);
    } catch (error) {
        console.error(`❌ Test runner encountered an error: ${error.message}`);
        process.exit(1);
    }
}

run(); 