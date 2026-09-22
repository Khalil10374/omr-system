@echo off
title OMR Enterprise System
cd /d "%~dp0"
echo Starting OMR Enterprise System on http://localhost:8501 ...
python -m streamlit run app.py --server.headless=false
pause
