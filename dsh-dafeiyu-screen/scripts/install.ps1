param([string]$Profile = 'desktop')
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path -Parent $PSScriptRoot
$lines = & (Join-Path $PSScriptRoot 'dependencies.ps1') -Component All
$info = ($lines | Select-Object -Last 1) | ConvertFrom-Json
$env:PATH=(Split-Path $info.node -Parent)+';'+$env:PATH
& $info.dsh plugin --profile $Profile add ('file:'+$appRoot.Replace('\','/'))
if ($LASTEXITCODE -ne 0) { throw 'DSH plugin installation failed. The dependency cache is retained; retry this installer.' }
Write-Host 'PANORAMA-360-SE-DSH-PET installed. Disable the old dsh-dafeiyu-screen plugin before enabling the new one.'
