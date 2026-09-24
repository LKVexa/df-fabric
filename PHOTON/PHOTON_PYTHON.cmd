@echo off
rem Resolve a Python 3.10+ interpreter, then run the requested Photon script.
setlocal
if not "%PYTHON%"=="" ( "%PYTHON%" -B %* & exit /b %ERRORLEVEL% )
py -3 -c "import sys;raise SystemExit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1 && ( py -3 -B %* & exit /b %ERRORLEVEL% )
python -c "import sys;raise SystemExit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1 && ( python -B %* & exit /b %ERRORLEVEL% )
python3 -c "import sys;raise SystemExit(0 if sys.version_info>=(3,10) else 1)" >nul 2>&1 && ( python3 -B %* & exit /b %ERRORLEVEL% )
echo [PHOTON] No Python 3.10+ interpreter found. Set PYTHON to an interpreter path. 1>&2
exit /b 127
