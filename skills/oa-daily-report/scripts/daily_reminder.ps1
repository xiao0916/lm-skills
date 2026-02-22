# 日报提醒 PowerShell 脚本
# 用于定时提醒填写 OA 日报

param(
    # 日报页面 URL
    [string]$Url = "https://oa.luckyxp.cn/pcc_web/#/daily-edit/create",
    # 通知标题
    [string]$Title = "日报提醒",
    # 通知内容
    [string]$Message = "17:30 了，该写日报啦！",
    # 通知显示时长（毫秒）
    [int]$DisplayTime = 10000
)

# 引入必要的 .NET 程序集
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# 创建通知图标对象
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.BalloonTipTitle = $Title
$notify.BalloonTipText = $Message
$notify.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
$notify.Visible = $true

# 显示气泡通知
try {
    $notify.ShowBalloonTip($DisplayTime)
    Write-Host "已显示通知: $Title - $Message"
} catch {
    Write-Warning "显示通知失败: $_"
}

# 立即打开浏览器
try {
    Start-Process $Url
    Write-Host "已打开浏览器: $Url"
} catch {
    Write-Warning "打开浏览器失败: $_"
}

# 等待一段时间后清理资源
Start-Sleep -Seconds ($DisplayTime / 1000 + 2)
$notify.Dispose()

Write-Host "日报提醒执行完成"
