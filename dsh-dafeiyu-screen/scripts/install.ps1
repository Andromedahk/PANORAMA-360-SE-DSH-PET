param([string]$Profile = 'desktop')
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path -Parent $PSScriptRoot
$cli = Get-Command dsh -ErrorAction SilentlyContinue
$desktopCli = Join-Path $env:LOCALAPPDATA 'Programs/DeepSeek Harness/resources/runtime/cli/bin/dsh.cmd'
if (-not $cli -and (Test-Path -LiteralPath $desktopCli)) { $cli = Get-Item -LiteralPath $desktopCli }
if ($cli) {
    $cliPath = if ($cli.Source) { $cli.Source } else { $cli.FullName }
    & $cliPath plugin --profile $Profile add ('file:' + $appRoot.Replace('\','/'))
    if ($LASTEXITCODE -ne 0) { throw 'DSH plugin installation failed.' }
} else {
    throw 'DSH CLI not found. Install the package from the DSH Plugins page using the local package folder, or run dsh plugin --profile desktop add file:<folder> with your DSH CLI.'
}
