@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 台股戰情室 v4.3.0 RWD Elite

echo =======================================================================
echo         正在檢查環境並啟動「台股戰情室 v4.3.0 RWD Elite」...
echo =======================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 找不到 Python 環境。請確認已安裝 Python 並勾選加入 PATH 環境變數。
    pause
    exit /b 1
)

echo [1/2] 檢查相依套件 (Streamlit / yfinance / Pandas)...
python -c "import streamlit, yfinance, pandas, plotly, requests, bs4" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 偵測到缺少必要套件，正在自動安裝中，請稍候...
    python -m pip install -r requirements.txt -q
    if errorlevel 1 (
        echo [ERROR] 套件安裝失敗，請檢查網路連線。
        pause
        exit /b 1
    )
) else (
    echo [OK] 核心套件檢查完備，極速啟動！
)

echo.
echo [2/2] 正在開啟台股戰情室介面...
python -m streamlit run app.py

pause
