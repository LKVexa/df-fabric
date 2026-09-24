@echo off
setlocal EnableExtensions
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root=(Resolve-Path '.').Path; $max=0; $long=''; Get-ChildItem -LiteralPath . -Recurse -File -Force | ForEach-Object { $n=$_.FullName.Length; if($n -gt $max){$max=$n;$long=$_.FullName} }; Write-Host ('Package root chars: ' + $root.Length); Write-Host ('Longest full path chars: ' + $max); Write-Host ('Longest path: ' + $long); if($max -le 259){Write-Host 'WINDOWS CLASSIC PATH PREFLIGHT: PASS'; exit 0}else{Write-Host 'WINDOWS CLASSIC PATH PREFLIGHT: FAIL - move the extracted folder closer to the drive root or enable Win32 long paths.'; exit 2}"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" pause
exit /b %RC%
