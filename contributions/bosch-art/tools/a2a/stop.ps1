$ErrorActionPreference = 'Stop'
$a2aRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$a2aPidFile = Join-Path $a2aRoot '.a2a/server.pid'
if (-not (Test-Path -LiteralPath $a2aPidFile)) { Write-Output 'A2A is not recorded as running.'; exit 0 }
$a2aServerId = [int](Get-Content -LiteralPath $a2aPidFile -Raw)
$a2aProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$a2aServerId"
$a2aExpectedScript = Join-Path $PSScriptRoot 'server.mjs'
if ($a2aProcess) {
    if (-not $a2aProcess.CommandLine.Contains($a2aExpectedScript)) { throw 'PID belongs to another process; nothing was stopped.' }
    & taskkill.exe /PID $a2aServerId /T /F
    if ($LASTEXITCODE -ne 0) { throw 'Unable to stop A2A process.' }
}
Remove-Item -LiteralPath $a2aPidFile -Force
Write-Output 'Stopped this project A2A server.'
