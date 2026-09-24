$ErrorActionPreference = 'Stop'
$Version = '2.1.2'
$Payload = Join-Path $PSScriptRoot 'DF-VM-Technical-Institute.payload.zip'
$Base = Join-Path $env:LOCALAPPDATA ('DF-VM-Technical-Institute\' + $Version)
$Install = Join-Path $Base 'app'
$Marker = Join-Path $Base 'payload.sha256'
$LogRoot = Join-Path $env:LOCALAPPDATA 'DF-VM-Technical-Institute\logs'
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$Log = Join-Path $LogRoot ('embedded-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.log')
function Log([string]$Message) { Add-Content -LiteralPath $Log -Value ((Get-Date -Format o) + ' ' + $Message) -Encoding UTF8 }
function Fail([string]$Message) {
    Log ('ERROR ' + $Message)
    try {
        $ws = New-Object -ComObject WScript.Shell
        [void]$ws.Popup($Message + "`r`n`r`nDiagnostic log:`r`n" + $Log, 0, 'DF VM Technical Institute - Extraction Error', 16)
    } catch { Write-Host $Message }
    exit 1
}
try {
    Log ('Embedded launcher root: ' + $PSScriptRoot)
    if (-not (Test-Path -LiteralPath $Payload -PathType Leaf)) { throw "Embedded payload is missing: $Payload" }
    $hash = (Get-FileHash -LiteralPath $Payload -Algorithm SHA256).Hash.ToLowerInvariant()
    Log ('Payload SHA-256: ' + $hash)
    $cachedHash = if (Test-Path -LiteralPath $Marker) { (Get-Content -LiteralPath $Marker -Raw).Trim().ToLowerInvariant() } else { '' }
    $required = @('index.html','assets\styles.css','assets\data.js','assets\site.js','Launch-DF-VM-Technical-Institute.cmd')
    $cacheValid = ($cachedHash -eq $hash)
    if ($cacheValid) {
        foreach ($rel in $required) { if (-not (Test-Path -LiteralPath (Join-Path $Install $rel) -PathType Leaf)) { $cacheValid = $false; break } }
    }
    if (-not $cacheValid) {
        Log 'Cache missing/stale; extracting to a staging directory.'
        $stagingBase = Join-Path $env:LOCALAPPDATA ('DF-VM-Technical-Institute\.staging-' + $Version + '-' + $PID)
        $staging = Join-Path $stagingBase 'app'
        if (Test-Path -LiteralPath $stagingBase) { Remove-Item -LiteralPath $stagingBase -Recurse -Force }
        New-Item -ItemType Directory -Force -Path $staging | Out-Null
        Expand-Archive -LiteralPath $Payload -DestinationPath $staging -Force
        foreach ($rel in $required) {
            $p = Join-Path $staging $rel
            if (-not (Test-Path -LiteralPath $p -PathType Leaf)) { throw "Payload validation failed; required file missing after extraction: $rel" }
        }
        if (Test-Path -LiteralPath $Base) { Remove-Item -LiteralPath $Base -Recurse -Force }
        New-Item -ItemType Directory -Force -Path $Base | Out-Null
        Move-Item -LiteralPath $staging -Destination $Install
        Set-Content -LiteralPath $Marker -Value $hash -Encoding ASCII
        if (Test-Path -LiteralPath $stagingBase) { Remove-Item -LiteralPath $stagingBase -Recurse -Force -ErrorAction SilentlyContinue }
        Log ('Installed validated payload to: ' + $Install)
    } else { Log ('Validated cached payload: ' + $Install) }
    $Launcher = Join-Path $Install 'Launch-DF-VM-Technical-Institute.cmd'
    Log ('Calling app launcher: ' + $Launcher)
    & $Launcher
    $rc = $LASTEXITCODE
    Log ('App launcher return code: ' + $rc)
    if ($rc -ne 0) { throw "The application launcher returned exit code $rc." }
    exit 0
} catch { Fail $_.Exception.Message }
