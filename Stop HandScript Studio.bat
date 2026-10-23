@echo off
cd /d "%~dp0"
title Stop HandScript Studio
echo.
echo Stopping HandScript Studio...
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not installed, so the app is not running.
  echo.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not running.
  echo Open Docker Desktop, wait until it says Docker is running, then double-click this file again.
  echo.
  pause
  exit /b 1
)

docker compose down
if errorlevel 1 (
  echo.
  echo HandScript Studio could not stop.
  echo Open Docker Desktop and double-click this file again.
  echo.
  pause
  exit /b 1
)

echo.
echo HandScript Studio is stopped. Your work is still saved.
echo Double-click "Start HandScript Studio" the next time you want to use it.
echo.
pause
