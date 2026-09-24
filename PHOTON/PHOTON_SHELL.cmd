@echo off
rem VEC1 app shell (loopback service + dashboard). Fabric surfaces report BLOCKED until bound.
call "%~dp0PHOTON_PYTHON.cmd" "%~dp0shell\VEC1\app.py" %*
