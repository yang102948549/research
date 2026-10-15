param([string]$Title = '', [string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$priorKey = [Environment]::GetEnvironmentVariable('KCI_API_KEY', 'Process')
$secureKey = $null
$keyPointer = [IntPtr]::Zero
$probeExit = 2
try {
    $secureKey = Read-Host 'KCI API key (hidden input; not saved)' -AsSecureString
    $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    [Environment]::SetEnvironmentVariable('KCI_API_KEY', [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer), 'Process')
    if ($Title) {
        & $Python -X utf8 (Join-Path $PSScriptRoot 'kci_probe.py') --title $Title
    } else {
        & $Python -X utf8 (Join-Path $PSScriptRoot 'kci_probe.py')
    }
    $probeExit = $LASTEXITCODE
}
finally {
    [Environment]::SetEnvironmentVariable('KCI_API_KEY', $priorKey, 'Process')
    if ($keyPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer) }
    if ($null -ne $secureKey) { $secureKey.Dispose() }
    $priorKey = $null
}
exit $probeExit
