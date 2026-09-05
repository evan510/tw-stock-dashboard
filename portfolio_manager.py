# -*- coding: utf-8 -*-
import json
import os
import pandas as pd
from data_engine import get_stock_history

PORTFOLIO_FILE = "user_portfolio.json"

def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        default_data = [
            {"symbol": "6467", "name": "泰合生技", "cost": 175.0, "shares": 1000, "buy_date": "2026-08-28"},
            {"symbol": "6696", "name": "仁新", "cost": 125.0, "shares": 1000, "buy_date": "2026-08-29"},
            {"symbol": "2330", "name": "台積電", "cost": 960.0, "shares": 1000, "buy_date": "2026-08-20"}
        ]
        save_portfolio(default_data)
        return default_data
    try:
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_holding(symbol, name, cost, shares, buy_date=None):
    items = load_portfolio()
    items.append({
        "symbol": str(symbol).strip(), "name": str(name).strip(),
        "cost": float(cost), "shares": int(shares), "buy_date": buy_date or "2026-09-01"
    })
    save_portfolio(items)

def remove_holding(index):
    items = load_portfolio()
    if 0 <= index < len(items):
        items.pop(index)
        save_portfolio(items)

def evaluate_holdings(holdings):
    evaluated = []
    total_cost, total_market_value = 0.0, 0.0
    for idx, item in enumerate(holdings):
        sym = item['symbol']
        df = get_stock_history(sym, period='2mo')
        if df.empty:
            continue
        last = df.iloc[-1]
        current_price = round(float(last['Close']), 2)
        cost = float(item['cost'])
        shares = int(item['shares'])
        cost_val = cost * shares
        market_val = current_price * shares
        profit = market_val - cost_val
        profit_pct = round(((current_price - cost) / cost) * 100, 2)
        total_cost += cost_val
        total_market_value += market_val
        ma20 = float(last['20MA']) if pd.notnull(last['20MA']) else current_price
        
        status_light = "🟢 正常續抱"
        advice = "均線架構健全，未破防守線，順勢抱緊波段。"
        if current_price < ma20:
            status_light = "🔴 跌破生命線"
            advice = "收盤已跌破 20MA 月線，短波段趨勢轉弱，建議紀律停損或分批獲利了結！"
        elif current_price < cost * 0.95:
            status_light = "🔴 觸發停損線"
            advice = f"虧損已超過 5% (現價 ${current_price})，原始進場假設失效，請果斷執行停損！"
        elif profit_pct >= 15.0:
            status_light = "🟢 獲利奔跑"
            advice = "波段獲利已達 15% 以上，可將防守線拉高至買進成本，讓利潤持續奔跑！"
            
        evaluated.append({
            'index': idx, 'symbol': sym, 'name': item['name'], 'cost': cost,
            'shares': shares, 'current_price': current_price, 'profit': round(profit, 0),
            'profit_pct': profit_pct, 'market_val': round(market_val, 0), 'ma20': round(ma20, 2),
            'status_light': status_light, 'advice': advice
        })
    total_profit = total_market_value - total_cost
    total_profit_pct = round((total_profit / total_cost) * 100, 2) if total_cost > 0 else 0.0
    summary = {
        'total_cost': round(total_cost, 0), 'total_market_value': round(total_market_value, 0),
        'total_profit': round(total_profit, 0), 'total_profit_pct': total_profit_pct
    }
    return evaluated, summary
