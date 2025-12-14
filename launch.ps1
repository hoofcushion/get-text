# 检查虚拟环境和脚本是否存在
if (-not (Test-Path venv\Scripts\Activate.ps1)) {throw "未找到venv虚拟环境"}
if (-not (Test-Path init.py)) {throw "未找到init.py脚本"}

# 构建转义参数字符串
$argString = "'$($args -replace "'", "''" -join "' '")'"

# 构建并执行命令
$command = @"
& .\venv\Scripts\Activate.ps1
Write-Host '虚拟环境已激活（进程ID: '`$PID'）'
python init.py $argString
Read-Host '按任意键退出'
"@

$process = Start-Process pwsh -ArgumentList '-NoProfile', '-Command', $command -Wait -PassThru

if ($process.ExitCode -ne 0) {throw "执行失败"}
Write-Host '执行完成'
exit 0
