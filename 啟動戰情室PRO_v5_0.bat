@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 台股短線極速戰情室 v5.0.0 Short-Term Pro (Gemini AI 旗艦版)

echo =======================================================================
echo     正在檢查環境並啟動「台股短線極速戰情室 v5.0.0 Pro」...
echo     模組精煉：5大短線聚焦模組 + Google Gemini AI 深度診斷 + 0 Token 快取
echo =======================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 找不到 Python 環境。請確認已安裝 Python 並勾選加入 PATH 環境變數。
    pause
    exit /b 1
)

echo [1/2] 檢查核心套件 (Streamlit / yfinance / Pandas / Plotly / Gemini)...
python -c "import streamlit, yfinance, pandas, plotly, requests, bs4, youtube_transcript_api" >nul 2>&1
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
echo [2/2] 正在開啟台股戰情室 v5.0 介面...
python -m streamlit run app.py

pause
