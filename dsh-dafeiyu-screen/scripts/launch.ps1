$ErrorActionPreference = 'Stop'
$appRoot = Split-Path -Parent $PSScriptRoot
$lines = & (Join-Path $PSScriptRoot 'dependencies.ps1') -Component App
$info = ($lines | Select-Object -Last 1) | ConvertFrom-Json
$env:PATH=(Split-Path $info.node -Parent)+';'+$env:PATH
Start-Process -FilePath $info.node -ArgumentList @('"'+(Join-Path $appRoot 'standalone.js')+'"') -WorkingDirectory $appRoot -WindowStyle Hidden
