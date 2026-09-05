# -*- coding: utf-8 -*-
import json
import os

CUSTOM_POOL_FILE = "custom_pool.json"

def load_custom_pool():
    if not os.path.exists(CUSTOM_POOL_FILE):
        initial = [
            {"symbol": "6467", "name": "泰合生技", "tag": "生技新藥/癌症劑型", "note": "關注興櫃量能與月線支撐"},
            {"symbol": "6696", "name": "仁新", "tag": "生技新藥/股票拆股", "note": "1拆10流動性大增"},
            {"symbol": "0050", "name": "元大台灣50", "tag": "市值型ETF", "note": "大盤權值核心"},
            {"symbol": "00878", "name": "國泰永續高股息", "tag": "高股息ETF", "note": "熱門存股標的"},
            {"symbol": "2330", "name": "台積電", "tag": "晶圓代工龍頭", "note": "先進製程需求旺盛"}
        ]
        save_custom_pool(initial)
        return initial
    try:
        with open(CUSTOM_POOL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_custom_pool(pool_data):
    with open(CUSTOM_POOL_FILE, "w", encoding="utf-8") as f:
        json.dump(pool_data, f, ensure_ascii=False, indent=2)

def add_to_custom_pool(symbol, name, tag="自選題材", note=""):
    pool = load_custom_pool()
    sym_clean = str(symbol).strip().upper()
    for item in pool:
        if item['symbol'] == sym_clean:
            item['name'] = name
            item['tag'] = tag
            item['note'] = note
            save_custom_pool(pool)
            return True, "已更新既有標的資料！"
    pool.append({
        "symbol": sym_clean,
        "name": name.strip(),
        "tag": tag.strip() if tag else "自選題材",
        "note": note.strip()
    })
    save_custom_pool(pool)
    return True, f"已成功將 {name} ({sym_clean}) 加入自選追蹤池！"

def remove_from_custom_pool(symbol):
    pool = load_custom_pool()
    sym_clean = str(symbol).strip().upper()
    new_pool = [item for item in pool if item['symbol'] != sym_clean]
    save_custom_pool(new_pool)
