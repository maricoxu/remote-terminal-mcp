#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

/**
 * 检查Python依赖是否正确安装
 */
function checkPythonDependencies() {
  console.log('🔍 检查Python依赖...');
  
  const requirementsPath = path.join(__dirname, '..', 'requirements.txt');
  
  if (!fs.existsSync(requirementsPath)) {
    console.log('❌ requirements.txt文件不存在');
    return false;
  }
  
  // 读取requirements.txt
  const requirements = fs.readFileSync(requirementsPath, 'utf8')
    .split('\n')
    .filter(line => line.trim() && !line.startsWith('#'))
    .map(line => line.split('>=')[0].split('==')[0].trim());
  
  // 映射包名到导入名
  const packageMapping = {
    'PyYAML': 'yaml',
    'colorama': 'colorama'
  };
  
  console.log(`📋 需要检查的依赖: ${requirements.join(', ')}`);
  
  let allInstalled = true;
  
  for (const pkg of requirements) {
    const importName = packageMapping[pkg] || pkg;
    try {
      // 尝试导入包
      execSync(`python3 -c "import ${importName}"`, { stdio: 'ignore' });
      console.log(`✅ ${pkg} - 已安装`);
    } catch (error) {
      try {
        // 尝试用python而不是python3
        execSync(`python -c "import ${importName}"`, { stdio: 'ignore' });
        console.log(`✅ ${pkg} - 已安装`);
      } catch (fallbackError) {
        console.log(`❌ ${pkg} - 未安装`);
        allInstalled = false;
      }
    }
  }
  
  return allInstalled;
}

/**
 * 尝试安装缺失的依赖
 */
function installMissingDependencies() {
  console.log('\n📦 尝试安装缺失的依赖...');
  
  const requirementsPath = path.join(__dirname, '..', 'requirements.txt');
  
  try {
    // 尝试用python3
    execSync(`python3 -m pip install -r "${requirementsPath}" --user`, { 
      stdio: 'inherit',
      timeout: 120000 // 2分钟超时
    });
    console.log('✅ 依赖安装完成');
    return true;
  } catch (error) {
    try {
      // 尝试用python
      execSync(`python -m pip install -r "${requirementsPath}" --user`, { 
        stdio: 'inherit',
        timeout: 120000
      });
      console.log('✅ 依赖安装完成');
      return true;
    } catch (fallbackError) {
      console.log('❌ 自动安装失败');
      console.log('\n🔧 请手动运行以下命令安装依赖:');
      console.log(`   pip install -r ${requirementsPath}`);
      console.log('   或者:');
      console.log(`   python3 -m pip install -r ${requirementsPath} --user`);
      return false;
    }
  }
}

/**
 * 主函数
 */
function main() {
  console.log('🚀 Remote Terminal MCP - 依赖检查工具\n');
  
  const isInstalled = checkPythonDependencies();
  
  if (isInstalled) {
    console.log('\n🎉 所有Python依赖都已正确安装！');
    process.exit(0);
  } else {
    console.log('\n⚠️  发现缺失的依赖');
    
    // 询问是否自动安装
    const readline = require('readline');
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });
    
    rl.question('是否尝试自动安装缺失的依赖? (y/N): ', (answer) => {
      rl.close();
      
      if (answer.toLowerCase() === 'y' || answer.toLowerCase() === 'yes') {
        const success = installMissingDependencies();
        
        if (success) {
          console.log('\n🔍 重新检查依赖...');
          const recheckResult = checkPythonDependencies();
          
          if (recheckResult) {
            console.log('\n🎉 所有依赖现在都已正确安装！');
            process.exit(0);
          } else {
            console.log('\n❌ 仍有依赖未正确安装，请手动处理');
            process.exit(1);
          }
        } else {
          process.exit(1);
        }
      } else {
        console.log('\n💡 请手动安装依赖后再使用');
        process.exit(1);
      }
    });
  }
}

// 如果直接运行此脚本
if (require.main === module) {
  main();
}

module.exports = {
  checkPythonDependencies,
  installMissingDependencies
}; 