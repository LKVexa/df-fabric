@echo off
setlocal EnableExtensions
cd /d "%~dp0"
call :find_python
if errorlevel 1 (
  echo REFUSED: Python 3.10 or newer was not found on PATH.
  echo Checked: py -3, python, python3.
  pause
  exit /b 3
)
%PY% -B -m unittest discover -s VEC1\tests -p "test_*.py" -v
if errorlevel 1 goto :fail
%PY% -B VEC1\app.py --verify-only
if errorlevel 1 goto :fail
echo VEC1 local verification PASS.
exit /b 0
:fail
echo VEC1 local verification FAILED.
pause
exit /b 1

:find_python
set "PY="
where py >nul 2>nul && (py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul && set "PY=py -3")
if defined PY exit /b 0
where python >nul 2>nul && (python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul && set "PY=python")
if defined PY exit /b 0
where python3 >nul 2>nul && (python3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul && set "PY=python3")
if defined PY exit /b 0
exit /b 1
