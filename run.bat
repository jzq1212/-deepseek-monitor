@echo off
title DeepSeek Monitor
cd /d "%~dp0backend"
echo DeepSeek Monitor - Starting...
echo Dashboard will open in your browser.
echo Close this window to stop the server.
echo.
python server.py
pause
