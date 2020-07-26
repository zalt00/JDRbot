@echo off

echo --------- Requirements being installed ---------

if not defined base (call "%~dp0\activate.cmd")

pip install -r "%base%\requirements.txt"
