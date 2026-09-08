# -*- coding: utf-8 -*-
import requests
import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alert_settings.json")

def load_alert_settings():
    default_settings = {
        "line_channel_token": "",
        "line_user_id": "",
        "line_token": "",  # legacy
        "webhook_url": "",
        "daily_digest": True,
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
            return data
    except Exception:
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

def send_daily_market_summary(picks_top5, regime, channel_token=None, user_id=None):
    """
    發送每日盤後 Top 5 狙擊焦點懶人包推播
    """
    from datetime import datetime
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    msg = f"【🚀 台股戰情室 盤後精選快報】\n📅 日期：{today_str}\n"
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"🎯 大盤體質：{regime.get('status', '多空拉鋸')} ({regime.get('score', 60)}分)\n"
    msg += f"👉 盤勢：{regime.get('desc', '')[:40]}...\n\n"
    msg += f"🔥 今日 Top 5 短線法人狙擊榜：\n"
    
    for idx, item in enumerate(picks_top5[:5], 1):
        streak_text = f"連買{item.get('streak_days', 1)}天" if item.get('streak_days', 0) > 1 else "爆量敲進"
        msg += f"{idx}. {item['name']} ({item['symbol']}) ${item['close']} ({item['pct_change']:+}%) | 評分 {item['short_score']}\n"
        msg += f"   • 型態：{item.get('trigger_type', '')} ({streak_text})\n"
        msg += f"   • 停損：${item['stop_loss']} | 目標：${item['target1']}\n"
        
    msg += f"━━━━━━━━━━━━━━━━\n"
    msg += f"💡 操盤紀律：嚴格執行停損，不盲目追高！"
    
    if channel_token and user_id:
        return send_line_messaging_api(msg, channel_access_token=channel_token, user_id=user_id)
    return send_smart_notification(msg, title="台股戰情室 盤後精選快報")

