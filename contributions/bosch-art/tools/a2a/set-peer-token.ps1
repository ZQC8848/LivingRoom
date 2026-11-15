$ErrorActionPreference = 'Stop'
$a2aRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$a2aEnvFile = Join-Path $a2aRoot '.env'
$a2aSecret = Read-Host 'Paste the teammate A2A token (hidden)' -AsSecureString
$a2aPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($a2aSecret)
try {
    $a2aPeerToken = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($a2aPointer)
    if ($a2aPeerToken.Length -lt 24 -or $a2aPeerToken.Contains("`n") -or $a2aPeerToken.Contains("`r")) { throw 'Invalid token.' }
    $a2aContents = [IO.File]::ReadAllText($a2aEnvFile)
    $a2aLines = $a2aContents -split '\r?\n' | ForEach-Object {
        if ($_ -match '^A2A_PEER_TOKEN=') { 'A2A_PEER_TOKEN=' + $a2aPeerToken } else { $_ }
    }
    [IO.File]::WriteAllText($a2aEnvFile, ($a2aLines -join "`n"), [Text.UTF8Encoding]::new($false))
    Write-Output 'Saved teammate token without printing it.'
} finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($a2aPointer); $a2aPeerToken = $null }
