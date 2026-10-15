param([string]$Title = '인공지능', [string]$Python = 'python', [string]$Output = '')
$ErrorActionPreference = 'Stop'
$priorKey = [Environment]::GetEnvironmentVariable('KCI_API_KEY', 'Process')
$secureKey = $null
$keyPointer = [IntPtr]::Zero
$probeExit = 2
try {
    if (-not $priorKey) {
        $secureKey = Read-Host 'KCI API key (hidden input; not saved)' -AsSecureString
        $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
        [Environment]::SetEnvironmentVariable('KCI_API_KEY', [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer), 'Process')
    }
    if (-not $Output) {
        $repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
        $Output = Join-Path $repoRoot ('validation/kci-pagination/live-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.json')
    }
    & $Python -X utf8 (Join-Path $PSScriptRoot 'kci_pagination_probe.py') --title $Title --output $Output
    $probeExit = $LASTEXITCODE
    if (Test-Path -LiteralPath $Output) { Write-Host ('Result file: ' + $Output) }
}
finally {
    [Environment]::SetEnvironmentVariable('KCI_API_KEY', $priorKey, 'Process')
    if ($keyPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer) }
    if ($null -ne $secureKey) { $secureKey.Dispose() }
    $priorKey = $null
}
exit $probeExit
