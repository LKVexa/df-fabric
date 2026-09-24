@echo off
setlocal
cd /d "%~dp0"
call "%~dp0VEC1_PYTHON.cmd" -B -m unittest discover -s tests -v
exit /b %ERRORLEVEL%
