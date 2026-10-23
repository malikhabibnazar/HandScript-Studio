@echo off
cd /d "%~dp0"
title HandScript Studio
echo.
echo HandScript Studio
echo =================
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not installed.
  echo.
  echo 1. Install it from https://www.docker.com/products/docker-desktop/
  echo 2. Open Docker Desktop and wait until it says Docker is running.
  echo 3. Double-click this file again.
  echo.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not running.
  echo.
  echo 1. Open Docker Desktop.
  echo 2. Wait until it says Docker is running.
  echo 3. Double-click this file again.
  echo.
  pause
  exit /b 1
)

echo Starting HandScript Studio.
echo The first time can take a long time while everything is downloaded.
echo Later starts are much faster. Please leave this window open.
echo.

docker compose up --build -d
if errorlevel 1 (
  echo.
  echo HandScript Studio could not start.
  echo Leave this window open and send a photo of this message.
  echo.
  pause
  exit /b 1
)

echo.
echo Waiting for the website to be ready...
set /a tries=0

:waitloop
set /a tries+=1
curl -fsS http://localhost:3000 >nul 2>&1
if not errorlevel 1 goto ready
if %tries% GEQ 60 goto stillstarting
timeout /t 5 /nobreak >nul
goto waitloop

:stillstarting
echo.
echo The website is still starting.
echo Open http://localhost:3000 in your browser.
echo If the page is not ready yet, wait a minute and refresh.
start "" http://localhost:3000
echo.
pause
exit /b 0

:ready
echo.
echo HandScript Studio is ready.
echo Open this address in your browser: http://localhost:3000
start "" http://localhost:3000
echo.
echo You can close this window. The app keeps running until you double-click "Stop HandScript Studio".
echo.
pause
