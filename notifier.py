# -*- coding: utf-8 -*-
import requests
import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alert_settings.json")

def load_alert_settings():
    if not os.path.exists(SETTINGS_FILE):
        default_settings = {
            "line_token": "",
            "webhook_url": "",
            "enable_stop_loss_alert": True,
            "enable_ma20_break_alert": True
        }
        save_alert_settings(default_settings)
        return default_settings
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"line_token": "", "webhook_url": "", "enable_stop_loss_alert": True, "enable_ma20_break_alert": True}

def save_alert_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def send_line_notify(message, token=None):
    """發送 Line Notify 訊息通知"""
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
            return True, "Line 通知發送成功！"
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
