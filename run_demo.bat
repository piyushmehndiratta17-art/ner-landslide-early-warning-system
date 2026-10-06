@echo off
title AI Landslide Early Warning System - NER Tech Expo
echo =====================================================================
echo  AI-Based Landslide Early Warning and Risk Monitoring System in NER
echo  Tech Expo Showcase Launcher
echo =====================================================================
echo.
echo Launching Streamlit Interactive Dashboard...
echo.

if exist .venv\Scripts\streamlit.exe (
    .\.venv\Scripts\streamlit.exe run app.py --server.port=8501 --browser.gatherUsageStats=false
) else (
    streamlit run app.py --server.port=8501 --browser.gatherUsageStats=false
)

pause
