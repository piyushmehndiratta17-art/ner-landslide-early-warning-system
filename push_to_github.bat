@echo off
title Push to GitHub - NER Landslide Early Warning System
echo =====================================================================
echo  Push Project to GitHub
echo =====================================================================
echo.
echo Make sure you have created a new empty repository on GitHub:
echo https://github.com/new
echo.

set /p REPO_URL="Enter your GitHub Repository URL (e.g., https://github.com/username/repo.git): "

if "%REPO_URL%"=="" (
    echo [ERROR] No URL entered. Aborting.
    pause
    exit /b
)

echo.
echo Setting remote origin to %REPO_URL%...
git remote remove origin 2>nul
git remote add origin %REPO_URL%

echo.
echo Pushing branch 'main' to GitHub...
git push -u origin main

echo.
echo =====================================================================
echo Done! Check your GitHub repository in your browser.
echo =====================================================================
pause
