@echo off
if not exist "%ProgramFiles%\Microsoft SDKs\Azure\CLI2\wbin\az.cmd" goto missing
call "%ProgramFiles%\Microsoft SDKs\Azure\CLI2\wbin\az.cmd" %*
exit /b %errorlevel%
:missing
echo Azure CLI not found. Install Microsoft.AzureCLI with winget, then retry.
exit /b 1
