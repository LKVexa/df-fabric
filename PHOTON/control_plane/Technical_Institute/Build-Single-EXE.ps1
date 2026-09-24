param(
    [switch]$ForceIExpress,
    [switch]$NoFallback
)

$ErrorActionPreference = 'Stop'
$Version = '2.1.2'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$App = Join-Path $Root 'app'
$Build = Join-Path $Root 'build'
$Payload = Join-Path $Build 'DF-VM-Technical-Institute.payload.zip'
$Target = Join-Path $Root ('DF-VM-Technical-Institute-v' + $Version + '.exe')
$Template = Join-Path $Build 'Bootstrap.template.cs'
$GeneratedSource = Join-Path $Build 'DF-VM-Technical-Institute.Bootstrap.generated.cs'
$BuildLog = Join-Path $Build ('build-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')

New-Item -ItemType Directory -Force -Path $Build | Out-Null

function Write-BuildLog([string]$Message) {
    $line = (Get-Date -Format o) + ' ' + $Message
    Add-Content -LiteralPath $BuildLog -Value $line -Encoding UTF8
    Write-Host $Message
}

function Assert-Input([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "Required $Label is missing: $Path" }
}

function New-Payload {
    Assert-Input $App 'app directory'
    if (Test-Path -LiteralPath $Payload) { Remove-Item -LiteralPath $Payload -Force }
    Write-BuildLog ('Creating payload from: ' + $App)
    Compress-Archive -Path (Join-Path $App '*') -DestinationPath $Payload -CompressionLevel Optimal
    $hash = (Get-FileHash -LiteralPath $Payload -Algorithm SHA256).Hash.ToLowerInvariant()
    $size = (Get-Item -LiteralPath $Payload).Length
    Write-BuildLog ('Payload bytes: ' + $size)
    Write-BuildLog ('Payload SHA-256: ' + $hash)
    return $hash
}

function New-EmbeddedBootstrapSource([string]$PayloadHash) {
    Assert-Input $Template 'C# bootstrap template'
    $bytes = [System.IO.File]::ReadAllBytes($Payload)
    $base64 = [Convert]::ToBase64String($bytes)

    # Keep individual C# string literals deliberately small. This avoids compiler/user-string
    # edge cases that can occur when one very large literal is emitted.
    $chunks = New-Object System.Collections.Generic.List[string]
    $chunkSize = 6000
    for ($i = 0; $i -lt $base64.Length; $i += $chunkSize) {
        $n = [Math]::Min($chunkSize, $base64.Length - $i)
        [void]$chunks.Add(('            "' + $base64.Substring($i, $n) + '"'))
    }
    $chunkText = $chunks -join ",`r`n"

    $source = Get-Content -LiteralPath $Template -Raw
    $source = $source.Replace('__VERSION__', $Version)
    $source = $source.Replace('__PAYLOAD_SHA__', $PayloadHash)
    $source = $source.Replace('__BASE64_CHUNKS__', $chunkText)
    Set-Content -LiteralPath $GeneratedSource -Value $source -Encoding ASCII
    Write-BuildLog ('Generated C# bootstrap source: ' + $GeneratedSource)
    return $source
}

function Invoke-DotNetBootstrapBuild([string]$Source) {
    $stageExe = Join-Path $Build ('DFVMTI-bootstrap-' + [Guid]::NewGuid().ToString('N') + '.exe')
    if (Test-Path -LiteralPath $stageExe) { Remove-Item -LiteralPath $stageExe -Force }

    Write-BuildLog ('Primary builder: Windows .NET Framework Add-Type (IExpress not required).')
    Write-BuildLog ('PowerShell: ' + $PSVersionTable.PSVersion.ToString() + ' / Edition: ' + $(if ($PSVersionTable.PSEdition) {$PSVersionTable.PSEdition} else {'Desktop'}))
    Write-BuildLog ('CLR: ' + [Environment]::Version.ToString())

    $refs = @(
        'System.dll',
        'System.Core.dll',
        'System.Windows.Forms.dll',
        'System.IO.Compression.dll',
        'System.IO.Compression.FileSystem.dll'
    )

    Add-Type -TypeDefinition $Source -Language CSharp -OutputAssembly $stageExe -OutputType WindowsApplication -ReferencedAssemblies $refs -ErrorAction Stop | Out-Null
    if (-not (Test-Path -LiteralPath $stageExe -PathType Leaf)) { throw 'Add-Type returned without creating the bootstrap EXE.' }

    $compiledBytes = [System.IO.File]::ReadAllBytes($stageExe)
    if ($compiledBytes.Length -lt 2 -or $compiledBytes[0] -ne 0x4D -or $compiledBytes[1] -ne 0x5A) { throw 'Compiled output does not have a Windows MZ executable header.' }

    if (Test-Path -LiteralPath $Target) { Remove-Item -LiteralPath $Target -Force }
    Move-Item -LiteralPath $stageExe -Destination $Target
    Write-BuildLog ('Primary .NET bootstrap build succeeded.')
    return 'DOTNET_EMBEDDED_BOOTSTRAP'
}

function Invoke-IExpressFallback {
    $IExpress = Join-Path $env:WINDIR 'System32\iexpress.exe'
    if (-not (Test-Path -LiteralPath $IExpress -PathType Leaf)) { throw 'IExpress fallback is unavailable.' }

    $EmbeddedCmd = Join-Path $Build 'Launch-DF-VM-Technical-Institute-Embedded.cmd'
    $EmbeddedPs1 = Join-Path $Build 'Launch-DF-VM-Technical-Institute-Embedded.ps1'
    Assert-Input $EmbeddedCmd 'IExpress embedded CMD'
    Assert-Input $EmbeddedPs1 'IExpress embedded PowerShell launcher'

    # IExpress is legacy and path-sensitive. Never feed it the distribution's nested path.
    # Build in a short disposable TEMP workspace and copy the finished EXE back afterward.
    $work = Join-Path $env:TEMP ('DFVMTI-' + [Guid]::NewGuid().ToString('N').Substring(0,8))
    New-Item -ItemType Directory -Force -Path $work | Out-Null
    $tempTarget = Join-Path $work 'DFVMTI.exe'
    $sed = Join-Path $work 'DFVMTI.sed'
    try {
        Copy-Item -LiteralPath $Payload -Destination (Join-Path $work 'DF-VM-Technical-Institute.payload.zip') -Force
        Copy-Item -LiteralPath $EmbeddedCmd -Destination (Join-Path $work 'Launch-DF-VM-Technical-Institute-Embedded.cmd') -Force
        Copy-Item -LiteralPath $EmbeddedPs1 -Destination (Join-Path $work 'Launch-DF-VM-Technical-Institute-Embedded.ps1') -Force
        $src = $work.TrimEnd('\') + '\'
        $sedText = @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=$tempTarget
FriendlyName=DF Portable VM Technical Institute v$Version
AppLaunched=cmd.exe /d /c Launch-DF-VM-Technical-Institute-Embedded.cmd
PostInstallCmd=<None>
AdminQuietInstCmd=cmd.exe /d /c Launch-DF-VM-Technical-Institute-Embedded.cmd
UserQuietInstCmd=cmd.exe /d /c Launch-DF-VM-Technical-Institute-Embedded.cmd
SourceFiles=SourceFiles
[Strings]
FILE0="DF-VM-Technical-Institute.payload.zip"
FILE1="Launch-DF-VM-Technical-Institute-Embedded.cmd"
FILE2="Launch-DF-VM-Technical-Institute-Embedded.ps1"
[SourceFiles]
SourceFiles0=$src
[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
"@
        Set-Content -LiteralPath $sed -Value $sedText -Encoding ASCII
        Copy-Item -LiteralPath $sed -Destination (Join-Path $Build 'DF-VM-Technical-Institute-IExpress-last.sed') -Force
        Write-BuildLog ('Fallback builder: IExpress in short TEMP workspace: ' + $work)
        & $IExpress /N /Q $sed
        $rc = $LASTEXITCODE
        Write-BuildLog ('IExpress exit code: ' + $rc)
        if (-not (Test-Path -LiteralPath $tempTarget -PathType Leaf)) { throw 'IExpress fallback did not create its TEMP target.' }
        if (Test-Path -LiteralPath $Target) { Remove-Item -LiteralPath $Target -Force }
        Copy-Item -LiteralPath $tempTarget -Destination $Target -Force
        return 'IEXPRESS_TEMP_FALLBACK'
    }
    finally {
        Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
    }
}

try {
    Write-BuildLog ('DF Portable VM Technical Institute v' + $Version + ' single-EXE build')
    Write-BuildLog ('Distribution root: ' + $Root)
    $payloadHash = New-Payload
    $method = $null

    if ($ForceIExpress) {
        $method = Invoke-IExpressFallback
    }
    else {
        try {
            $source = New-EmbeddedBootstrapSource $payloadHash
            $method = Invoke-DotNetBootstrapBuild $source
        }
        catch {
            Write-BuildLog ('Primary .NET bootstrap build failed: ' + $_.Exception.Message)
            if ($NoFallback) { throw }
            Write-BuildLog 'Attempting isolated IExpress fallback.'
            $method = Invoke-IExpressFallback
        }
    }

    if (-not (Test-Path -LiteralPath $Target -PathType Leaf)) { throw 'Build completed without a final EXE.' }
    $targetHash = (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash
    $targetSize = (Get-Item -LiteralPath $Target).Length
    Write-BuildLog ('Created: ' + $Target)
    Write-BuildLog ('Build method: ' + $method)
    Write-BuildLog ('EXE bytes: ' + $targetSize)
    Write-BuildLog ('EXE SHA-256: ' + $targetHash)
    Write-BuildLog ('Build log: ' + $BuildLog)
    Write-BuildLog 'The generated EXE is not Authenticode-signed. Sign it separately if your deployment policy requires code signing.'
    exit 0
}
catch {
    Write-BuildLog ('FATAL: ' + $_.Exception.ToString())
    Write-Host ''
    Write-Host ('Build failed. Diagnostic log: ' + $BuildLog) -ForegroundColor Red
    Write-Host 'You can still run the institute directly with app\Launch-DF-VM-Technical-Institute.cmd.' -ForegroundColor Yellow
    exit 1
}
