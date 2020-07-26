@echo off

if not defined path2go (goto define) else (goto duplicate_env)

:define
set /p "path2go=Please enter the path to the main directory: "
goto duplicate_env

:duplicate_env
echo --------- Environment being duplicated ---------

mkdir "%path2go%\commands"

for %%f in ("%base%\commands\*.cmd") do (
    echo - %%f being copied
    copy "%%f" "%path2go%\commands"
    )
if not exist "%path2go%\shell.cmd" (
    echo - shell.cmd being copied
    copy "%~dp0\..\shell.cmd" "%path2go%\shell.cmd"
    )
goto :eof

:eof
set path2go=
