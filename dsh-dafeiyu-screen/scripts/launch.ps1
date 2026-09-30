$ErrorActionPreference = 'Stop'
$appRoot = Split-Path -Parent $PSScriptRoot
$nodeBinary = Join-Path $appRoot 'runtime/node.exe'
if (-not (Test-Path -LiteralPath $nodeBinary)) {
    $nodeBinary = (Get-Command node -ErrorAction Stop).Source
}
$major = [int]((& $nodeBinary --version).TrimStart('v').Split('.')[0])
if ($major -lt 22) { throw 'Please use Node.js 22.19+ or the portable Windows package.' }
Start-Process -FilePath $nodeBinary -ArgumentList @('"' + (Join-Path $appRoot 'standalone.js') + '"') -WorkingDirectory $appRoot -WindowStyle Hidden
