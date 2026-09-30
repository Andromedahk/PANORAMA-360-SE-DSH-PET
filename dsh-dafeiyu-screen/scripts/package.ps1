param([string]$NodePath, [string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $appRoot 'dist' }
if (-not $NodePath) { $NodePath = Join-Path $appRoot 'runtime/node.exe' }
New-Item -ItemType Directory -Force -Path (Join-Path $appRoot 'bin/python'), (Join-Path $appRoot 'runtime'), $OutputDirectory | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $appRoot 'bin/python/python.exe'))) {
    $pythonZip = Join-Path $env:TEMP ('dafeiyu-python-' + [guid]::NewGuid().ToString('N') + '.zip')
    Invoke-WebRequest 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip' -OutFile $pythonZip
    Expand-Archive -LiteralPath $pythonZip -DestinationPath (Join-Path $appRoot 'bin/python') -Force
    Add-Content -LiteralPath (Join-Path $appRoot 'bin/python/python310._pth') -Value '../../worker'
    Remove-Item -LiteralPath $pythonZip
}
if (-not (Test-Path -LiteralPath $NodePath)) {
    $nodeZip = Join-Path $env:TEMP ('dafeiyu-node-' + [guid]::NewGuid().ToString('N') + '.zip')
    $nodeExtract = Join-Path $env:TEMP ('dafeiyu-node-' + [guid]::NewGuid().ToString('N'))
    Invoke-WebRequest 'https://nodejs.org/dist/v24.19.0/node-v24.19.0-win-x64.zip' -OutFile $nodeZip
    Expand-Archive -LiteralPath $nodeZip -DestinationPath $nodeExtract
    $NodePath = Join-Path $nodeExtract 'node-v24.19.0-win-x64/node.exe'
    Remove-Item -LiteralPath $nodeZip
}
$runtimeNode = Join-Path $appRoot 'runtime/node.exe'
if ([IO.Path]::GetFullPath($NodePath) -ne [IO.Path]::GetFullPath($runtimeNode)) {
    Copy-Item -LiteralPath $NodePath -Destination $runtimeNode -Force
}
Invoke-WebRequest 'https://raw.githubusercontent.com/nodejs/node/v24.19.0/LICENSE' -OutFile (Join-Path $appRoot 'runtime/LICENSE')
Push-Location $appRoot
try {
    npm ci --ignore-scripts --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
    npm pack --ignore-scripts --pack-destination $OutputDirectory
    if ($LASTEXITCODE -ne 0) { throw 'npm pack failed' }
    & (Join-Path $appRoot 'bin/python/python.exe') (Join-Path $PSScriptRoot 'package_portable.py') --output $OutputDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Portable packaging failed' }
} finally { Pop-Location }
