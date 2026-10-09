@echo off
if not exist "%~dp0..\.cache\railway-v1\cli\node_modules\@railway\cli\bin\railway.exe" goto missing
"%~dp0..\.cache\railway-v1\cli\node_modules\@railway\cli\bin\railway.exe" %*
exit /b %errorlevel%
:missing
echo Railway CLI binary is not installed under E:\Fusion\.cache\railway-v1\cli.
exit /b 1
