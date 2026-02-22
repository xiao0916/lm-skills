# 任务计划删除脚本
# 用于取消每日 17:30 的日报提醒定时任务

param(
    # 任务名称
    [string]$TaskName = "OA-Daily-Report-Reminder"
)

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
Write-ColorOutput "   OA 日报提醒定时任务取消" "Cyan"
Write-ColorOutput "========================================" "Cyan"
Write-Host ""

# 检查任务是否存在
Write-ColorOutput "检查任务是否存在..." "White"
$existingTask = schtasks /Query /TN $TaskName 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput "定时任务未注册，无需取消" "Yellow"
    Write-Host ""
    Write-ColorOutput "提示: 可以运行 setup_reminder.ps1 创建定时任务" "White"
    exit 0
}

# 显示当前任务信息
Write-ColorOutput "当前任务信息:" "Cyan"
$existingTask | Select-Object -First 10
Write-Host ""

# 确认删除
Write-ColorOutput "正在删除定时任务..." "Yellow"
Write-Host ""

# 删除任务
$deleteCmd = "schtasks /Delete /TN `"$TaskName`" /F"
$output = Invoke-Expression $deleteCmd 2>&1
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host ""
    Write-ColorOutput "========================================" "Green"
    Write-ColorOutput "  ✅ 定时任务已成功删除！" "Green"
    Write-ColorOutput "========================================" "Green"
    Write-Host ""
    Write-ColorOutput "提示: 可以运行 setup_reminder.ps1 重新创建定时任务" "White"
} else {
    Write-Host ""
    Write-ColorOutput "========================================" "Red"
    Write-ColorOutput "  ❌ 定时任务删除失败" "Red"
    Write-ColorOutput "========================================" "Red"
    Write-Host ""
    Write-ColorOutput "错误信息:" "Red"
    Write-Host $output
    Write-Host ""
    Write-ColorOutput "提示: 删除任务计划可能需要管理员权限" "Yellow"
    exit 1
}
