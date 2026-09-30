param([string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
$appRoot=Split-Path -Parent $PSScriptRoot
if (-not $OutputDirectory) { $OutputDirectory=Join-Path $appRoot 'dist' }
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$lines=& (Join-Path $PSScriptRoot 'dependencies.ps1') -Component Node
$info=($lines | Select-Object -Last 1) | ConvertFrom-Json
$npm=Join-Path (Split-Path $info.node -Parent) 'npm.cmd'
$env:PATH=(Split-Path $info.node -Parent)+';'+$env:PATH
Push-Location $appRoot
try {
    $result=& $npm pack --ignore-scripts --json --pack-destination $OutputDirectory
    if ($LASTEXITCODE -ne 0) { throw 'npm pack failed' }
    $pack=($result | ConvertFrom-Json)[0]
    $stage=Join-Path $OutputDirectory ('stage-'+[guid]::NewGuid().ToString('N'))
    $folder=Join-Path $stage 'PANORAMA-360-SE-DSH-PET'
    foreach ($entry in $pack.files) {
        $dest=Join-Path $folder $entry.path
        New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
        Copy-Item -LiteralPath (Join-Path $appRoot $entry.path) -Destination $dest
    }
    $zip=Join-Path $OutputDirectory ('PANORAMA-360-SE-DSH-PET-'+$pack.version+'-windows-x64.zip')
    Compress-Archive -LiteralPath $folder -DestinationPath $zip -Force
    Write-Host $zip
    Write-Host ('npm archive: '+(Join-Path $OutputDirectory $pack.filename))
} finally { Pop-Location }
