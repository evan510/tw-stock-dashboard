# -*- coding: utf-8 -*-
import requests
import json
import os
import threading

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alert_settings.json")

def load_alert_settings():
    default_settings = {
        "line_channel_token": "",
        "line_user_id": "",
        "line_token": "",  # legacy
        "webhook_url": "",
        "daily_digest": True,
        "enable_schedule_0830": True,
        "enable_schedule_0930": True,
        "enable_schedule_1530": True,
        "only_on_trading_days": True,
        "enable_stop_loss_alert": True,
        "enable_ma20_break_alert": True
    }
    if not os.path.exists(SETTINGS_FILE):
        save_alert_settings(default_settings)
        return default_settings
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 填補缺省值
            for k, v in default_settings.items():
                if k not in data:
                    data[k] = v
            # 支援環境變數優先覆蓋 (供 GitHub Actions / Streamlit Secrets 使用)
            if os.environ.get("LINE_CHANNEL_TOKEN"):
                data["line_channel_token"] = os.environ["LINE_CHANNEL_TOKEN"].strip()
            if os.environ.get("LINE_USER_ID"):
                data["line_user_id"] = os.environ["LINE_USER_ID"].strip()
            if os.environ.get("WEBHOOK_URL"):
                data["webhook_url"] = os.environ["WEBHOOK_URL"].strip()
            return data
    except Exception:
        # 當找不到檔案時，仍檢查環境變數
        if os.environ.get("LINE_CHANNEL_TOKEN"):
            default_settings["line_channel_token"] = os.environ["LINE_CHANNEL_TOKEN"].strip()
        if os.environ.get("LINE_USER_ID"):
            default_settings["line_user_id"] = os.environ["LINE_USER_ID"].strip()
        if os.environ.get("WEBHOOK_URL"):
            default_settings["webhook_url"] = os.environ["WEBHOOK_URL"].strip()
        return default_settings

def save_alert_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def send_line_messaging_api(message, channel_access_token=None, user_id=None):
    """
    使用 LINE 官方帳號 Messaging API (Push Message) 發送訊息給指定 User ID
    官方每月提供免費 200 則 Push 訊息額度
    """
    settings = load_alert_settings()
    token = (channel_access_token or settings.get("line_channel_token", "")).strip()
    target_user = (user_id or settings.get("line_user_id", "")).strip()

    if not token:
        return False, "未設定 LINE Channel Access Token"
    if not target_user:
        return False, "未設定 LINE User ID"

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "to": target_user,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        if res.status_code == 200:
            return True, "LINE 官方機器人訊息推播成功！"
        else:
            try:
                err_info = res.json().get("message", res.text)
            except Exception:
                err_info = res.text
            return False, f"LINE 發送失敗 (HTTP {res.status_code}): {err_info}"
    except Exception as e:
        return False, f"連線錯誤: {str(e)}"

def send_line_notify(message, token=None):
    """相容舊版 Line Notify 訊息通知"""
    if not token:
        settings = load_alert_settings()
        token = settings.get("line_token", "").strip()
    if not token:
        return False, "未設定 Line Notify Token"
    
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": message}
    try:
        res = requests.post(url, headers=headers, data=data, timeout=6)
        if res.status_code == 200:
            return True, "Line Notify 通知發送成功！"
        else:
            return False, f"發送失敗 (代碼 {res.status_code}): {res.text}"
    except Exception as e:
        return False, f"連線錯誤: {str(e)}"

def send_webhook_alert(title, message, webhook_url=None):
    """發送通用 Webhook (Discord / Slack / Telegram Bot 相容)"""
    if not webhook_url:
        settings = load_alert_settings()
        webhook_url = settings.get("webhook_url", "").strip()
    if not webhook_url:
        return False, "未設定 Webhook URL"
    
    payload = {"content": f"**{title}**\n{message}", "text": f"{title}\n{message}"}
    try:
        res = requests.post(webhook_url, json=payload, timeout=6)
        if res.status_code in [200, 204]:
            return True, "Webhook 通知發送成功！"
        else:
            return False, f"發送失敗 ({res.status_code}): {res.text}"
    except Exception as e:
        return False, f"連線錯誤: {str(e)}"

def send_smart_notification(message, title="【台股戰情室】"):
    """
    智慧統一推播通道：
    1. 優先使用 LINE Messaging API (官方 Bot)
    2. 若未設定，則嘗試 Webhook (Discord / Slack)
    3. 最後嘗試舊版 Line Notify
    """
    settings = load_alert_settings()
    if settings.get("line_channel_token") and settings.get("line_user_id"):
        return send_line_messaging_api(message)
    elif settings.get("webhook_url"):
        return send_webhook_alert(title, message)
    elif settings.get("line_token"):
        return send_line_notify(message)
    else:
        return False, "尚未設定任何推播管道 (請至第 7 頁設定 LINE Messaging API 或 Webhook)"

def send_morning_market_digest(radar=None, channel_token=None, user_id=None):
    """
    【08:30 晨間早盤快報】
    推播夜盤總結 + 美股台積電ADR + 那指期貨 + 今日早盤預期跳空
    """
    from datetime import datetime
    import data_engine
    if not radar:
        radar = getattr(data_engine, 'get_night_session_radar', lambda: {})()

    today_str = datetime.now().strftime('%Y-%m-%d')
    wtx = radar.get('wtx', {})
    tsm = radar.get('tsm', {})
    nq = radar.get('nq', {})
    impact_pts = radar.get('impact_pts', 0)
    sentiment = radar.get('gap_sentiment', '平盤震盪')
    advice = radar.get('advice', '')

    msg = f"【☀️ 台股戰情室 08:30 晨間早盤快報】\n📅 日期：{today_str}\n"
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"🌙 夜盤與美股跨市場總結：\n"
    msg += f"• 🇹🇼 台指期夜盤：{wtx.get('price', '--')} ({wtx.get('change', 0):+,.1f} 點 / {wtx.get('pct', 0):+,.2f}%)\n"
    msg += f"• 🇺🇸 台積電 ADR：${tsm.get('price', 0):,.2f} ({tsm.get('change', 0):+,.2f} / {tsm.get('pct', 0):+,.2f}%)\n"
    msg += f"• 🇺🇸 那斯達克期：{nq.get('price', 0):,.1f} ({nq.get('change', 0):+,.1f} / {nq.get('pct', 0):+,.2f}%)\n\n"
    msg += f"🎯 今日開盤跳空預估：\n"
    msg += f"👉 預估情境：{sentiment}\n"
    msg += f"👉 指數衝擊：約 {impact_pts:+,.0f} 點\n\n"
    msg += f"💡 開盤操盤導航：\n{advice}\n"
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"🔔 盤中早盤起漲雷達將於 09:30 為您更新！"

    if channel_token and user_id:
        return send_line_messaging_api(msg, channel_access_token=channel_token, user_id=user_id)
    return send_smart_notification(msg, title="台股戰情室 晨間早盤快報")

def send_intraday_surge_digest(surge_picks=None, channel_token=None, user_id=None):
    """
    【09:30 早盤起漲雷達快報】
    推播早盤預估爆量起漲 Top 3 飆股
    """
    from datetime import datetime
    import strategy_engine
    if surge_picks is None:
        surge_picks = getattr(strategy_engine, 'get_intraday_volume_surge_radar', lambda limit=10: [])(limit=5)

    today_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    top3 = surge_picks[:3] if surge_picks else []

    msg = f"【⚡ 台股戰情室 09:30 早盤起漲雷達】\n⏰ 時間：{today_str}\n"
    msg += f"━━━━━━━━━━━━━━━━\n"
    if top3:
        msg += f"🔥 盤中爆量剛起漲 Top 3 突擊標的：\n\n"
        for idx, item in enumerate(top3, 1):
            msg += f"{idx}. {item['name']} ({item['symbol']}) 現價 ${item['close']} ({item['pct_change']:+}%)\n"
            msg += f"   • 預估量倍數：{item['proj_ratio']}x 20MA (預估全日 {item['proj_vol']:,} 張)\n"
            msg += f"   • 訊號特徵：{item['signal_tag']}\n"
            msg += f"   • 進場參考：${item['buy_zone']} | 停損：${item['stop_loss']}\n"
    else:
        msg += f"ℹ️ 目前早盤無顯著爆量起漲標的，市場以冷靜防守或震盪為主。\n"
        
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"💡 操盤提醒：起漲標的嚴禁開盤市價盲目追高，等待拉回均線守穩再分批介入！"

    if channel_token and user_id:
        return send_line_messaging_api(msg, channel_access_token=channel_token, user_id=user_id)
    return send_smart_notification(msg, title="台股戰情室 早盤起漲雷達")

def send_daily_market_summary(picks_top5, regime, channel_token=None, user_id=None):
    """
    【15:30 盤後精選快報】
    發送每日盤後 Top 5 狙擊焦點懶人包推播
    """
    from datetime import datetime
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    msg = f"【🚀 台股戰情室 15:30 盤後精選快報】\n📅 日期：{today_str}\n"
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"🎯 今日大盤體質：{regime.get('status', '多空拉鋸')} ({regime.get('score', 60)}分)\n"
    msg += f"👉 盤勢速覽：{regime.get('desc', '')[:45]}...\n\n"
    msg += f"🔥 今日 Top 5 法人連續加碼狙擊榜：\n"
    
    for idx, item in enumerate(picks_top5[:5], 1):
        streak_text = f"連買{item.get('streak_days', 1)}天" if item.get('streak_days', 0) > 1 else "爆量敲進"
        msg += f"{idx}. {item['name']} ({item['symbol']}) ${item['close']} ({item['pct_change']:+}%) | 評分 {item['short_score']}\n"
        msg += f"   • 型態：{item.get('trigger_type', '')} ({streak_text})\n"
        msg += f"   • 停損：${item['stop_loss']} | 目標：${item['target1']}\n"
        
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"💡 操盤紀律：嚴格執行停損，保護獲利與本金！"
    
    if channel_token and user_id:
        return send_line_messaging_api(msg, channel_access_token=channel_token, user_id=user_id)
    return send_smart_notification(msg, title="台股戰情室 盤後精選快報")

# ================= 自動排程推播守護引擎 (Background Scheduler Daemon) =================
_scheduler_started = False
_scheduler_lock = threading.Lock()

def _run_scheduler_loop():
    """
    背景常駐循環：
    在營業日 (週一至週五) 定時檢查並觸發推播：
    - 08:30 晨間早盤快報
    - 09:30 早盤起漲雷達
    - 15:30 盤後精選快報
    """
    import time
    from datetime import datetime
    import data_engine
    import strategy_engine

    last_sent_slots = {}  # 格式: {"2026-09-08_0830": True}

    while True:
        try:
            now = datetime.now()
            today_str = now.strftime('%Y-%m-%d')
            weekday = now.weekday()  # 0=Mon, 4=Fri, 5=Sat, 6=Sun
            hm = now.strftime('%H:%M')

            # 僅在營業日 (週一至週五) 執行自動推播
            if weekday < 5:
                settings = load_alert_settings()

                # 若使用者開啟「休市/非交易日不發送」，進行證交所休市日檢核
                if settings.get("only_on_trading_days", True):
                    is_trading, reason = getattr(data_engine, 'is_tw_trading_day', lambda: (True, ''))(now.date())
                    if not is_trading:
                        time.sleep(60)
                        continue

                # 1. 08:30 晨間早盤快報 (容許窗口 08:30 ~ 08:34)
                if settings.get("enable_schedule_0830", True) and "08:30" <= hm <= "08:34":
                    slot_key = f"{today_str}_0830"
                    if slot_key not in last_sent_slots:
                        radar = getattr(data_engine, 'get_night_session_radar', lambda: {})()
                        send_morning_market_digest(radar=radar)
                        last_sent_slots[slot_key] = True

                # 2. 09:30 早盤起漲雷達 (容許窗口 09:30 ~ 09:34)
                if settings.get("enable_schedule_0930", True) and "09:30" <= hm <= "09:34":
                    slot_key = f"{today_str}_0930"
                    if slot_key not in last_sent_slots:
                        surge_picks = getattr(strategy_engine, 'get_intraday_volume_surge_radar', lambda limit=5: [])(limit=5)
                        send_intraday_surge_digest(surge_picks=surge_picks)
                        last_sent_slots[slot_key] = True

                # 3. 15:30 盤後精選快報 (容許窗口 15:30 ~ 15:34)
                if settings.get("enable_schedule_1530", True) and "15:30" <= hm <= "15:34":
                    slot_key = f"{today_str}_1530"
                    if slot_key not in last_sent_slots:
                        picks = getattr(strategy_engine, 'get_short_term_catalyst_picks', lambda limit=5: [])(limit=5)
                        regime = getattr(strategy_engine, 'calculate_market_regime', lambda: {})()
                        send_daily_market_summary(picks, regime)
                        last_sent_slots[slot_key] = True

            # 清理前幾天的 slot 記錄以防字典過大
            if len(last_sent_slots) > 30:
                current_keys = [k for k in last_sent_slots.keys() if today_str in k]
                last_sent_slots.clear()
                for k in current_keys:
                    last_sent_slots[k] = True

        except Exception:
            pass

        time.sleep(25)  # 每 25 秒檢查一次

def ensure_scheduler_running():
    """確保守護排程線程在背景只啟動一次"""
    global _scheduler_started
    with _scheduler_lock:
        if not _scheduler_started:
            t = threading.Thread(target=_run_scheduler_loop, daemon=True, name="TwStockAlertScheduler")
            t.start()
            _scheduler_started = True


