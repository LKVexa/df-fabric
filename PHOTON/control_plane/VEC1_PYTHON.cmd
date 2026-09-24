@echo off
setlocal
rem VEC1 Python bootstrap for Windows. PYTHON may point to an explicit python.exe.
if defined PYTHON (
  "%PYTHON%" %*
  exit /b %ERRORLEVEL%
)
where py >nul 2>&1
if not errorlevel 1 (
  py -3 %*
  exit /b %ERRORLEVEL%
)
where python >nul 2>&1
if not errorlevel 1 (
  python %*
  exit /b %ERRORLEVEL%
)
where python3 >nul 2>&1
if not errorlevel 1 (
  python3 %*
  exit /b %ERRORLEVEL%
)
echo ERROR: Python 3 was not found. Set PYTHON to the full path of python.exe, or install the Windows Python launcher. 1>&2
exit /b 127
