@echo off
setlocal
cd /d "%~dp0"
call START_VEC1.cmd --preflight
exit /b %ERRORLEVEL%
