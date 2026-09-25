# Syntax-only: never executes the companion provisioning scripts.
$ErrorActionPreference = 'Stop'
$failed = $false
Get-ChildItem (Join-Path $PSScriptRoot '../host/windows') -Filter *.ps1 | ForEach-Object {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
    if ($parseErrors.Count -gt 0) {
        $parseErrors | ForEach-Object { Write-Output $_ }
        $failed = $true
    }
}
if ($failed) { exit 1 }
Write-Output "PowerShell $($PSVersionTable.PSVersion) companion syntax PASS"
