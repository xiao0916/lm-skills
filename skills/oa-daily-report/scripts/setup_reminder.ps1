# 任务计划注册脚本
# 用于注册每日 17:30 的日报提醒定时任务

param(
    # 提醒时间（24小时制）
    [string]$Time = "17:30",
    # 任务名称
    [string]$TaskName = "OA-Daily-Report-Reminder"
)

# 脚本所在目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$reminderScript = Join-Path $scriptDir "daily_reminder.ps1"

# 颜色输出函数
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    $colors = @{
        "Green" = [ConsoleColor]::Green
        "Yellow" = [ConsoleColor]::Yellow
        "Red" = [ConsoleColor]::Red
        "Cyan" = [ConsoleColor]::Cyan
        "White" = [ConsoleColor]::White
    }
    Write-Host $Message -ForegroundColor $colors[$Color]
}

# 显示标题
Write-ColorOutput "========================================" "Cyan"
Write-ColorOutput "   OA 日报提醒定时任务注册" "Cyan"
Write-ColorOutput "========================================" "Cyan"
Write-Host ""

# 检查提醒脚本是否存在
Write-ColorOutput "检查文件..." "White"
if (-not (Test-Path $reminderScript)) {
    Write-ColorOutput "错误: 找不到 reminder 脚本: $reminderScript" "Red"
    exit 1
}
Write-ColorOutput "提醒脚本: OK" "Green"

# 检查是否已存在同名任务
Write-Host "检查现有任务..." -NoNewline
$existingTask = schtasks /Query /TN $TaskName 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-ColorOutput " 已存在" "Yellow"
    Write-Host ""
    Write-ColorOutput "当前任务信息:" "Yellow"
    $existingTask | Select-Object -First 5
    Write-Host ""
    Write-ColorOutput "如需重新注册，请先运行 remove_reminder.ps1 删除现有任务" "Yellow"
    exit 0
}
Write-ColorOutput " 无" "Green"

# 创建任务计划
Write-Host ""
Write-ColorOutput "正在创建任务计划..." "White"
Write-Host "  任务名称: $TaskName"
Write-Host "  执行时间: 每天 $Time"
Write-Host "  执行脚本: $reminderScript"
Write-Host ""

# 构建 schtasks 命令
# 使用 /F 强制创建，如果已存在会覆盖
$psPath = "powershell.exe"
$psArgs = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$reminderScript`""
$createCmd = "schtasks /Create /TN `"$TaskName`" /TR `"$psPath $psArgs`" /SC DAILY /ST $Time /F"

# 执行命令
$output = Invoke-Expression $createCmd 2>&1
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host ""
    Write-ColorOutput "========================================" "Green"
    Write-ColorOutput "  ✅ 定时任务创建成功！" "Green"
    Write-ColorOutput "========================================" "Green"
    Write-Host ""
    Write-ColorOutput "任务详情:" "Cyan"
    Write-Host "  - 任务名称: $TaskName"
    Write-Host "  - 执行时间: 每天 $Time"
    Write-Host "  - 执行脚本: $reminderScript"
    Write-Host ""
    Write-ColorOutput "查看任务: schtasks /Query /TN `"$TaskName`"" "White"
    Write-ColorOutput "删除任务: .\remove_reminder.ps1" "White"
} else {
    Write-Host ""
    Write-ColorOutput "========================================" "Red"
    Write-ColorOutput "  ❌ 定时任务创建失败" "Red"
    Write-ColorOutput "========================================" "Red"
    Write-Host ""
    Write-ColorOutput "错误信息:" "Red"
    Write-Host $output
    Write-Host ""
    Write-ColorOutput "提示: 创建任务计划需要管理员权限" "Yellow"
    Write-ColorOutput "请以管理员身份运行 PowerShell 后重试" "Yellow"
    exit 1
}
