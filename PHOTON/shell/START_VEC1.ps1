$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
function Find-CompatiblePython {
    $candidates = @(
        @{ Exe = "py"; Prefix = @("-3") },
        @{ Exe = "python"; Prefix = @() },
        @{ Exe = "python3"; Prefix = @() }
    )
    foreach ($c in $candidates) {
        if (-not (Get-Command $c.Exe -ErrorAction SilentlyContinue)) { continue }
        & $c.Exe @($c.Prefix) -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' *> $null
        if ($LASTEXITCODE -eq 0) { return $c }
    }
    return $null
}
$Py = Find-CompatiblePython
if (-not $Py) { Write-Error "REFUSED: Python 3.10 or newer was not found on PATH."; exit 3 }
& $Py.Exe @($Py.Prefix) -B "VEC1\app.py" @args
exit $LASTEXITCODE
