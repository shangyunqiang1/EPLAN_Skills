[CmdletBinding()]
param([string]$Python = 'python', [switch]$IncludeSymbolSearch)
$ErrorActionPreference = 'Stop'
if ($env:EPLAN_SKILLS_DATA_DIR) {
    $dataRoot = [IO.Path]::GetFullPath($env:EPLAN_SKILLS_DATA_DIR)
} else {
    $dataRoot = Join-Path $env:LOCALAPPDATA 'EPLAN_Skills'
}
$installArgs = @((Join-Path $PSScriptRoot 'runtime_environment.py'), '--data-dir', $dataRoot)
if ($IncludeSymbolSearch) { $installArgs += '--symbols' }
& $Python @installArgs
if ($LASTEXITCODE -ne 0) { throw 'Installation failed; the previous runtime environment remains available.' }
