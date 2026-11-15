$ErrorActionPreference = 'Stop'
$a2aRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$a2aLogs = Join-Path $a2aRoot '.a2a'
New-Item -ItemType Directory -Path $a2aLogs -Force | Out-Null
$a2aNode = (Get-Command node.exe -ErrorAction Stop).Source
$a2aCodex = (Get-Command codex.exe -ErrorAction Stop).Source
$env:A2A_CODEX_BIN = $a2aCodex
$a2aScript = Join-Path $PSScriptRoot 'server.mjs'
$a2aExisting = Join-Path $a2aLogs 'server.pid'
if (Test-Path -LiteralPath $a2aExisting) {
    $a2aExistingId = [int](Get-Content -LiteralPath $a2aExisting -Raw)
    $a2aExistingProcess = Get-Process -Id $a2aExistingId -ErrorAction SilentlyContinue
    if ($a2aExistingProcess -and $a2aExistingProcess.ProcessName -eq 'node') {
        Write-Output "A2A process already running: $a2aExistingId"
        exit 0
    }
}
$a2aProcess = Start-Process -FilePath $a2aNode -ArgumentList @('"' + $a2aScript + '"') -WorkingDirectory $a2aRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $a2aLogs 'server.stdout.log') -RedirectStandardError (Join-Path $a2aLogs 'server.stderr.log') -PassThru
$a2aPort = 41241
$a2aPortLine = Select-String -LiteralPath (Join-Path $a2aRoot '.env') -Pattern '^A2A_PORT=(\d+)' | Select-Object -First 1
if ($a2aPortLine) { $a2aPort = [int]$a2aPortLine.Matches[0].Groups[1].Value }
for ($a2aAttempt = 0; $a2aAttempt -lt 30; $a2aAttempt++) {
    try {
        $a2aHealth = Invoke-RestMethod -Uri "http://127.0.0.1:$a2aPort/health" -TimeoutSec 1
        if ($a2aHealth.ok) { Write-Output "A2A server ready on 127.0.0.1:$a2aPort; PID $($a2aProcess.Id)"; exit 0 }
    } catch { }
    if ($a2aProcess.HasExited) { throw "A2A stopped during startup. See $a2aLogs/server.stderr.log" }
    Start-Sleep -Milliseconds 150
}
throw "A2A did not become ready. See $a2aLogs/server.stderr.log"
