# -*- coding: utf-8 -*-
"""
GitHub Actions 專用自動排程推播腳本
支援時段參數:
  python run_scheduled_push.py 0830  # 晨間早盤快報
  python run_scheduled_push.py 0930  # 早盤起漲雷達
  python run_scheduled_push.py 1530  # 盤後精選快報
"""
import sys
import os
from datetime import datetime

# 確保輸出支援 UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import data_engine
import strategy_engine
import notifier

def main():
    arg_slot = sys.argv[1] if len(sys.argv) > 1 else "auto"

    # 強制鎖定台灣時間 (UTC+8)
    from datetime import timezone, timedelta
    tw_tz = timezone(timedelta(hours=8))
    now_tw = datetime.now(tw_tz)
    today_date = now_tw.date()
    hm = now_tw.strftime('%H%M')

    # 自動判斷時段
    if arg_slot == "auto":
        # 07:00 ~ 09:10 判定為 08:30 晨間早盤快報
        if "0700" <= hm <= "0910":
            slot = "0830"
        # 09:11 ~ 11:30 判定為 09:30 早盤起漲雷達
        elif "0911" <= hm <= "1130":
            slot = "0930"
        # 其餘時段 (11:31 之後) 判定為 15:30 盤後精選快報
        else:
            slot = "1530"
    else:
        slot = arg_slot

    print(f"=== [台股戰情室 GitHub Actions 排程推播] 執行時段: {slot} (輸入: {arg_slot}) | 台灣時間: {now_tw.strftime('%Y-%m-%d %H:%M:%S')} ===")

    settings = notifier.load_alert_settings()

    # 1. 檢核是否為台股開盤營業日 (休市/週末不發送)
    if settings.get("only_on_trading_days", True):
        is_trading, reason = data_engine.is_tw_trading_day(today_date)
        if not is_trading:
            print(f"[INFO] 今日非台股開盤交易日 ({reason})，依設定跳過推播！")
            return
        else:
            print(f"[OK] 今日為台股開盤營業日 ({reason})，繼續執行推播。")

    # 2. 檢查排程各別開關
    if slot == "0830" and not settings.get("enable_schedule_0830", True):
        print("[INFO] 08:30 晨間早盤快報排程已關閉，跳過執行。")
        return
    elif slot == "0930" and not settings.get("enable_schedule_0930", True):
        print("[INFO] 09:30 早盤起漲雷達排程已關閉，跳過執行。")
        return
    elif slot == "1530" and not settings.get("enable_schedule_1530", True):
        print("[INFO] 15:30 盤後精選快報排程已關閉，跳過執行。")
        return

    # 3. 依時段觸發推播
    if slot == "0830":
        print("[1/2] 正在抓取夜盤與跨市場風向儀數據...")
        radar = data_engine.get_night_session_radar()
        print("[2/2] 發送 08:30 晨間早盤快報...")
        ok, msg = notifier.send_morning_market_digest(radar=radar)
        print(f"推播結果: {msg}")

    elif slot == "0930":
        print("[1/2] 正在掃描盤中預估爆量起漲飆股...")
        surge_picks = strategy_engine.get_intraday_volume_surge_radar(limit=5)
        print(f"[2/2] 發送 09:30 早盤起漲雷達 (找到 {len(surge_picks)} 檔)...")
        ok, msg = notifier.send_intraday_surge_digest(surge_picks=surge_picks)
        print(f"推播結果: {msg}")

    elif slot == "1530":
        print("[1/2] 正在分析大盤體質與盤後三大法人連續加碼 Top 5...")
        picks = strategy_engine.get_short_term_catalyst_picks(limit=5)
        regime = strategy_engine.calculate_market_regime()
        print(f"[2/2] 發送 15:30 盤後精選快報 (找到 {len(picks)} 檔)...")
        ok, msg = notifier.send_daily_market_summary(picks, regime)
        print(f"推播結果: {msg}")

    else:
        print(f"[ERROR] 未知的時段參數: {slot}")

if __name__ == '__main__':
    main()
