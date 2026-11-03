[CmdletBinding()]
param(
    [string]$Python = 'python',
    [switch]$IncludeSymbolSearch
)
$ErrorActionPreference = 'Stop'
$pluginRoot = Split-Path -Parent $PSScriptRoot
if ($env:EPLAN_SKILLS_DATA_DIR) {
    $dataRoot = [IO.Path]::GetFullPath($env:EPLAN_SKILLS_DATA_DIR)
} else {
    $dataRoot = Join-Path $env:LOCALAPPDATA 'EPLAN_Skills'
}
New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
$venvPath = Join-Path $dataRoot 'venv'
& $Python -c 'import sys,struct; assert sys.version_info >= (3,10), "Python 3.10+ required"; assert struct.calcsize("P")==8, "64-bit Python required"'
if ($LASTEXITCODE -ne 0) { throw 'Python prerequisite check failed.' }
if (-not (Test-Path -LiteralPath (Join-Path $venvPath 'Scripts/python.exe'))) {
    & $Python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create the Python virtual environment.' }
}
$venvPython = Join-Path $venvPath 'Scripts/python.exe'
$requirements = Join-Path $pluginRoot 'vendor/eplan-mcp/eplan-p8-mcp-server/mcp_server/requirements.txt'
& $venvPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) { throw 'Cannot install EPLAN MCP dependencies.' }
if ($IncludeSymbolSearch) {
    & $venvPython -m pip install sentence-transformers pillow requests
    if ($LASTEXITCODE -ne 0) { throw 'Cannot install optional symbol-search dependencies.' }
}
& $venvPython -c 'from importlib.metadata import version; print("mcp="+version("mcp")); print("pythonnet="+version("pythonnet"))'
if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }
Write-Host "Ready: $venvPython. Restart the plugin MCP process. EPLAN Remote Client access must be enabled in EPLAN settings."
