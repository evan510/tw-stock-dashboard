@echo off
title 台股戰情室 v4.1.0 RWD Elite
echo =======================================================================
echo         正在檢查環境並啟動「台股戰情室 v4.1.0 RWD Elite」...
echo =======================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please make sure Python is installed and added to PATH.
    pause
    exit
)

echo [1/2] Verifying dependencies...
python -m pip install -r requirements.txt -q

echo.
echo [2/2] Opening Dashboard in browser...
python -m streamlit run app.py

pause
