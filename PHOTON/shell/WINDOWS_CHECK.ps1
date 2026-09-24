$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
& "$PSScriptRoot\START_VEC1.ps1" --preflight
exit $LASTEXITCODE
