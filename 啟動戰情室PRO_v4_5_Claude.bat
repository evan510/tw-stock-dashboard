@echo off
chcp 65001 >nul
title 台股戰情室 PRO v4.5-Claude
color 0a

echo.
echo  ╔═══════════════════════════════════════════════════════╗
echo  ║    📈 台股戰情室 PRO v4.5-Claude                    ║
echo  ║    🎙️ YT 分析師 × 論壇情緒 × AI 作戰結論           ║
echo  ╚═══════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: 檢查 Python 環境
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 找不到 Python，請確認 Python 已安裝並加入 PATH
    pause
    exit /b 1
)

:: 安裝相依套件（首次執行）
if exist requirements.txt (
    echo [1/2] 檢查並安裝相依套件...
    pip install -r requirements.txt -q
)

:: 啟動 Streamlit
echo [2/2] 啟動台股戰情室 PRO v4.5-Claude...
echo.
echo  瀏覽器將自動開啟：http://localhost:8502
echo  按下 Ctrl+C 可停止服務
echo.

streamlit run app.py --server.port 8502 --server.headless false --browser.gatherUsageStats false

pause
