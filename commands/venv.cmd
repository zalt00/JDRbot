@echo off

echo ------- Python Virtual Environment being created -------

python -m venv "%~dp0\..\venv"
call "%~dp0\activate.cmd"
call install_requirements.cmd
