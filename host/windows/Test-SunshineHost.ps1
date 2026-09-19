<#
.SYNOPSIS
Print Windows Sunshine host health diagnostics.
.DESCRIPTION
Read-only report of Sunshine/Tailscale services, physical adapters, IPv4
addresses, Sunshine firewall rules, and NVIDIA driver information when available.
Inspect individual results; a completed report does not prove streaming works.
.EXAMPLE
.\Test-SunshineHost.ps1
.EXAMPLE
Get-Help .\Test-SunshineHost.ps1 -Full
.NOTES
Output contains private network addresses. Review before sharing.
#>
[CmdletBinding()]
param()
$ErrorActionPreference='Continue'
Write-Host '=== Sunshine Host Health ===' -ForegroundColor Cyan
Get-Service -Name '*Sunshine*','Tailscale' -ErrorAction SilentlyContinue | Format-Table Name,Status,StartType -AutoSize
Write-Host "`nNetwork adapters" -ForegroundColor Cyan
Get-NetAdapter -Physical -ErrorAction SilentlyContinue | Format-Table Name,Status,LinkSpeed,MacAddress -AutoSize
Write-Host "`nIP addresses" -ForegroundColor Cyan
Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object {$_.IPAddress -notlike '127.*'} | Format-Table InterfaceAlias,IPAddress,PrefixLength -AutoSize
Write-Host "`nSunshine firewall rules" -ForegroundColor Cyan
Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object DisplayName -Match 'Sunshine' | Select-Object DisplayName,Enabled,Direction,Action | Format-Table -AutoSize
if (Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue) {
    Write-Host "`nNVIDIA encoder host" -ForegroundColor Cyan
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
}
