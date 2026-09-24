@echo off
rem Photon dispatch.  Usage:  PHOTON.cmd [status|ctl|shell] [args...]
setlocal
set "CMD=%~1"
if "%CMD%"=="" set "CMD=status"
shift
if /I "%CMD%"=="status" ( call "%~dp0PHOTON\PHOTON_STATUS.cmd" %1 %2 %3 %4 %5 %6 %7 %8 %9 & exit /b %ERRORLEVEL% )
if /I "%CMD%"=="ctl"    ( call "%~dp0PHOTON\PHOTON_CTL.cmd"    %1 %2 %3 %4 %5 %6 %7 %8 %9 & exit /b %ERRORLEVEL% )
if /I "%CMD%"=="shell"  ( call "%~dp0PHOTON\PHOTON_SHELL.cmd"  %1 %2 %3 %4 %5 %6 %7 %8 %9 & exit /b %ERRORLEVEL% )
echo [PHOTON] Unknown command "%CMD%".  Use: status ^| ctl ^| shell 1>&2
exit /b 2
