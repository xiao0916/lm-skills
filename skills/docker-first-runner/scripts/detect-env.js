const { execSync } = require('child_process');
const os = require('os');

// 运行命令并返回结果
function runCommand(cmd) {
  try {
    return { success: true, output: execSync(cmd, { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] }).trim() };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

// 从输出中提取版本号
function extractVersion(output) {
  const match = output.match(/(\d+\.\d+\.\d+)/);
  return match ? match[1] : null;
}

// 检测 Docker
const dockerInstalled = runCommand('docker --version');
let dockerUsable = false, dockerError = null, dockerSuggestion = null;
let dockerVersion = dockerInstalled.success ? extractVersion(dockerInstalled.output) : null;

if (dockerInstalled.success) {
  dockerUsable = runCommand('docker ps').success;
  if (!dockerUsable) {
    dockerError = 'Docker 守护进程未运行';
    dockerSuggestion = '启动 Docker 守护进程或检查权限';
  }
} else {
  dockerError = 'Docker 未安装';
  dockerSuggestion = '安装 Docker: https://docs.docker.com/get-docker/';
}

// 检测 Python
let pythonAvailable = false, pythonVersion = null, pythonPath = null, pythonError = null;
const python3Check = runCommand('python3 --version');
if (python3Check.success) {
  pythonAvailable = true;
  pythonVersion = extractVersion(python3Check.output);
  const pathCheck = runCommand('which python3');
  pythonPath = pathCheck.success ? pathCheck.output : null;
} else {
  const pythonCheck = runCommand('python --version');
  if (pythonCheck.success) {
    pythonAvailable = true;
    pythonVersion = extractVersion(pythonCheck.output);
    const pathCheck = runCommand('which python');
    pythonPath = pathCheck.success ? pathCheck.output : null;
  } else {
    pythonError = '未找到 Python';
  }
}

// 检测 Node.js
const nodeCheck = runCommand('node --version');
const nodeAvailable = nodeCheck.success;
const nodeVersion = nodeCheck.success ? extractVersion(nodeCheck.output) : null;
const nodePathCheck = nodeCheck.success ? runCommand('which node') : { success: false };
const nodePath = nodePathCheck.success ? nodePathCheck.output : null;
const nodeError = nodeCheck.success ? null : '未找到 Node.js';

// 输出 JSON 结果
console.log(JSON.stringify({
  docker: { available: dockerInstalled.success, usable: dockerUsable, version: dockerVersion, error: dockerError, suggestion: dockerSuggestion },
  python: { available: pythonAvailable, version: pythonVersion, path: pythonPath, error: pythonError },
  node: { available: nodeAvailable, version: nodeVersion, path: nodePath, error: nodeError },
  platform: os.platform(),
  timestamp: new Date().toISOString()
}, null, 2));
