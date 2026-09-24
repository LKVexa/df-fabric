@echo off
rem VEC1 control-plane CLI (vecctl). Host surfaces report UNBOUND until a bridge is written.
call "%~dp0PHOTON_PYTHON.cmd" "%~dp0control_plane\vec1\vecctl.py" %*
