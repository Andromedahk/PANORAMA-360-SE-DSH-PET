param(
    [ValidateSet('Python','Node','App','DSH','All')][string]$Component = 'All',
    [string]$CacheRoot = $(if ($env:PANORAMA_RUNTIME_HOME) { $env:PANORAMA_RUNTIME_HOME } else { Join-Path $env:LOCALAPPDATA 'PANORAMA-360-SE-DSH-PET/runtimes' }),
    [switch]$ForceDownload
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }
$appRoot = Split-Path -Parent $PSScriptRoot
$manifest = Get-Content -Raw -LiteralPath (Join-Path $appRoot 'dependencies.json') | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path $CacheRoot | Out-Null

function Test-Runtime([string]$Path, [string]$Kind) {
    if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return $false }
    try {
        if ($Kind -eq 'python') {
            $output = & $Path -I -c "import sys,struct,ctypes;print('.'.join(map(str,sys.version_info[:3])) if struct.calcsize('P')==8 else '0.0.0')" 2>$null
        } else { $output = & $Path --version 2>$null }
        return $LASTEXITCODE -eq 0 -and [version]($output.Trim().TrimStart('v')) -ge [version]$manifest.$Kind.minimum
    } catch { return $false }
}
function Get-Runtime([string]$Kind) {
    $spec = $manifest.$Kind
    if (-not $ForceDownload) {
        $override = if ($Kind -eq 'python') { $env:DAFEIYU_PYTHON } else { $env:PANORAMA_NODE }
        $command = Get-Command ($Kind + '.exe') -ErrorAction SilentlyContinue
        foreach ($candidate in @($override, $command.Source)) {
            if (Test-Runtime $candidate $Kind) { return $candidate }
        }
    }
    $target = Join-Path $CacheRoot ($Kind + '-' + $spec.version)
    $exe = Join-Path $target ($Kind + '.exe')
    if (Test-Runtime $exe $Kind) { return $exe }
    $lockName = 'Local\PanoramaPetDependency-' + $Kind
    $mutex = New-Object System.Threading.Mutex($false, $lockName)
    $locked = $false
    try {
        try { $locked = $mutex.WaitOne(300000) } catch [System.Threading.AbandonedMutexException] { $locked = $true }
        if (-not $locked) { throw 'Another dependency download is still running. Retry shortly.' }
        if (Test-Runtime $exe $Kind) { return $exe }
        $stage = Join-Path $CacheRoot ($Kind + '-stage-' + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $stage | Out-Null
        $zip = Join-Path $stage 'download.zip'
        Write-Host "Downloading $Kind $($spec.version) from its official site..."
        $ok = $false
        for ($attempt=1; $attempt -le 3; $attempt++) {
            try { Invoke-WebRequest -UseBasicParsing -Uri $spec.url -OutFile $zip -TimeoutSec 180; $ok=$true; break }
            catch { if ($attempt -eq 3) { throw }; Start-Sleep -Seconds 2 }
        }
        if (-not $ok -or (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $spec.sha256) { throw 'Dependency SHA-256 mismatch; archive was not executed.' }
        $unpack = Join-Path $stage 'unpack'
        Expand-Archive -LiteralPath $zip -DestinationPath $unpack
        $source = if ($Kind -eq 'node') { Join-Path $unpack $spec.folder } else { $unpack }
        if (-not (Test-Runtime (Join-Path $source ($Kind+'.exe')) $Kind)) { throw 'Downloaded runtime failed verification.' }
        # Preserve any damaged prior install instead of deleting computed trees.
        if (Test-Path -LiteralPath $target) { Rename-Item -LiteralPath $target -NewName ((Split-Path $target -Leaf) + '.old-' + [guid]::NewGuid().ToString('N')) }
        Move-Item -LiteralPath $source -Destination $target
        Remove-Item -LiteralPath $zip
        return $exe
    } finally { if ($locked) { $mutex.ReleaseMutex() }; $mutex.Dispose() }
}
$result = @{}
if ($Component -in @('Python','All')) { $result.python=Get-Runtime 'python' }
if ($Component -in @('Node','App','DSH','All')) {
    $result.node=Get-Runtime 'node'
    $env:PATH=(Split-Path $result.node -Parent)+';'+$env:PATH
}
if ($Component -in @('App','All')) {
    $npm = Join-Path (Split-Path $result.node -Parent) 'npm.cmd'
    if (-not (Test-Path -LiteralPath $npm)) { throw 'npm.cmd is missing beside Node. Re-run with -ForceDownload.' }
    Push-Location $appRoot
    try {
        & $npm ci --omit=dev --ignore-scripts --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw 'npm dependency installation failed; check network access and retry.' }
    } finally { Pop-Location }
}
if ($Component -in @('DSH','All')) {
    $dsh = Get-Command dsh.cmd -ErrorAction SilentlyContinue
    $desktop = Join-Path $env:LOCALAPPDATA 'Programs/DeepSeek Harness/resources/runtime/cli/bin/dsh.cmd'
    if ($dsh -and -not $ForceDownload) { $result.dsh=$dsh.Source }
    elseif ((Test-Path -LiteralPath $desktop) -and -not $ForceDownload) { $result.dsh=$desktop }
    else {
        $prefix = Join-Path $CacheRoot ('dsh-'+$manifest.dsh.version)
        $cli = Join-Path $prefix 'node_modules/@deepseek-ai/dsh/bin/dsh.mjs'
        $npm = Join-Path (Split-Path $result.node -Parent) 'npm.cmd'
        # npm's generated shim is the stable entry point, independent of package internals.
        $shim = Join-Path $prefix 'node_modules/.bin/dsh.cmd'
        if (-not (Test-Path -LiteralPath $shim)) {
            New-Item -ItemType Directory -Force -Path $prefix | Out-Null
            @{private=$true;allowScripts=$manifest.dsh.installScripts} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $prefix 'package.json') -Encoding UTF8
            & $npm install --prefix $prefix --no-audit --no-fund --save-exact ($manifest.dsh.package+'@'+$manifest.dsh.version)
            if ($LASTEXITCODE -ne 0) { throw 'DSH installation failed.' }
        }
        if (-not (Test-Path -LiteralPath $shim)) {
            New-Item -ItemType Directory -Force -Path $prefix | Out-Null
            @{private=$true;allowScripts=$manifest.dsh.installScripts} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $prefix 'package.json') -Encoding UTF8 throw 'DSH CLI shim missing after installation.' }
        $result.dsh=$shim
    }
}
$result | ConvertTo-Json -Compress
