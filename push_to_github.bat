@echo off
title Push to GitHub - NER Landslide Early Warning System
echo =====================================================================
echo  Pushing to GitHub
echo  Repository: https://github.com/piyushmehndiratta17-art/ner-landslide-early-warning-system
echo =====================================================================
echo.
git push -u origin main
echo.
if %errorlevel% equ 0 (
    echo =====================================================================
    echo  [SUCCESS] All code has been pushed successfully to GitHub!
    echo =====================================================================
) else (
    echo [ERROR] Push failed or was cancelled. Please check your GitHub credentials.
)
echo.
pause
