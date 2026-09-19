<#
.SYNOPSIS
Install/configure the Windows Sunshine streaming host companion.
.DESCRIPTION
Run on the Windows host, not the Steam Deck. Requests Administrator rights,
installs Sunshine through its official visible installer when absent, checks
host integration, and opens local setup. Account pairing remains interactive.
.PARAMETER InstallTailscale
Also request Tailscale installation and login for private remote reachability.
.PARAMETER ConfigureWake
Attempt supported network-adapter wake configuration. BIOS/firmware settings
and wake support must still be checked on the host.
.EXAMPLE
.\Setup-SunshineHost.ps1 -InstallTailscale -ConfigureWake
.EXAMPLE
Get-Help .\Setup-SunshineHost.ps1 -Full
.NOTES
May change installed software, services and host configuration. Review the
companion README. This script is never executed by the Deck installer.
#>
[CmdletBinding()]
param(
    [switch]$InstallTailscale,
    [switch]$ConfigureWake
)
$ErrorActionPreference = 'Stop'

function Test-Admin {
    $id=[Security.Principal.WindowsIdentity]::GetCurrent()
    $p=New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
if (-not (Test-Admin)) {
    Write-Host 'Re-launching as Administrator...'
    $args = "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($InstallTailscale) { $args += ' -InstallTailscale' }
    if ($ConfigureWake) { $args += ' -ConfigureWake' }
    Start-Process powershell.exe -Verb RunAs -ArgumentList $args
    exit
}

Write-Host '=== deckctl Sunshine Windows host setup ===' -ForegroundColor Cyan
$winget = Get-Command winget.exe -ErrorAction SilentlyContinue
$sunSvc = Get-Service -Name '*Sunshine*' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $sunSvc) {
    Write-Host 'Sunshine not detected. Downloading the current official GitHub MSI and launching it visibly.' -ForegroundColor Yellow
    try {
        $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/LizardByte/Sunshine/releases/latest' -Headers @{ 'User-Agent'='deckctl-host-kit' }
        $assetName = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'Sunshine-Windows-ARM64-installer.msi' } else { 'Sunshine-Windows-AMD64-installer.msi' }
        $asset = $release.assets | Where-Object name -eq $assetName | Select-Object -First 1
        if (-not $asset) { throw "Could not locate $assetName in the latest Sunshine release." }
        $msi = Join-Path $env:TEMP $assetName
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $msi -UseBasicParsing
        Start-Process msiexec.exe -Wait -ArgumentList @('/i', "`"$msi`"")
    } catch {
        Write-Host "Automatic Sunshine MSI retrieval failed: $($_.Exception.Message)" -ForegroundColor Yellow
        Start-Process 'https://github.com/LizardByte/Sunshine/releases/latest'
    }
} else {
    Write-Host "Sunshine service found: $($sunSvc.Name) / $($sunSvc.Status)" -ForegroundColor Green
}

$ts = Get-Service -Name 'Tailscale' -ErrorAction SilentlyContinue
if (-not $ts -and $InstallTailscale) {
    if ($winget) {
        Write-Host 'Installing Tailscale interactively...' -ForegroundColor Yellow
        winget install --id tailscale.tailscale --exact --interactive --accept-source-agreements --accept-package-agreements
    } else {
        Start-Process 'https://tailscale.com/download/windows'
    }
} elseif ($ts) {
    Write-Host "Tailscale service found: $($ts.Status)" -ForegroundColor Green
} else {
    Write-Host 'Tailscale not detected. Re-run with -InstallTailscale if this host should join your tailnet.' -ForegroundColor Yellow
}

Write-Host "`nPhysical network adapters / MACs" -ForegroundColor Cyan
$adapters = Get-NetAdapter -Physical -ErrorAction SilentlyContinue | Where-Object Status -ne 'Disabled'
$adapters | Format-Table Name, InterfaceDescription, Status, LinkSpeed, MacAddress -AutoSize

if ($ConfigureWake) {
    Write-Host 'Attempting to enable Wake on Magic Packet on supported adapters. BIOS/UEFI Wake-on-LAN must still be enabled manually.' -ForegroundColor Yellow
    foreach ($a in $adapters) {
        try {
            Set-NetAdapterPowerManagement -Name $a.Name -WakeOnMagicPacket Enabled -ErrorAction Stop
            Write-Host "Enabled magic-packet wake: $($a.Name)" -ForegroundColor Green
        } catch {
            Write-Host "Could not configure wake on $($a.Name): $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host 'Wake settings were not changed. Re-run with -ConfigureWake after reviewing the adapter/BIOS settings.'
}

Write-Host "`nSunshine firewall rules" -ForegroundColor Cyan
Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object DisplayName -Match 'Sunshine' | Select-Object DisplayName,Enabled,Direction,Action | Format-Table -AutoSize

Write-Host "`nNext steps" -ForegroundColor Cyan
Write-Host '1. Finish Sunshine first-run Web UI credentials/configuration.'
Write-Host '2. Pair the Steam Deck Moonlight client.'
Write-Host '3. Confirm Wake-on-LAN works while the PC is asleep.'
Write-Host '4. From the Deck run: deckctl remote test <host-name>'
Write-Host '5. Prefer wired Ethernet on the host whenever possible.'
