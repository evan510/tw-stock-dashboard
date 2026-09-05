# -*- coding: utf-8 -*-
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import config
import logging
# 關閉 yfinance 預設在終端機噴出的 404 與 No data found 雜訊
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

def resolve_stock(query_text):
    clean = str(query_text).strip()
    if not clean:
        return "", ""
    if clean in config.STOCK_NAME_MAP:
        mapped = config.STOCK_NAME_MAP[clean]
        if mapped.isdigit():
            full_name = config.STOCK_NAME_MAP.get(mapped, clean)
            return mapped, full_name
        else:
            return clean, mapped
    for name, sym in config.STOCK_NAME_MAP.items():
        if not name.isdigit() and (clean in name or name in clean):
            return sym, config.STOCK_NAME_MAP.get(sym, name)
    if clean.isdigit() and len(clean) >= 4:
        return clean, f"台股 {clean}"
    return clean, clean

def get_twse_market_active_stocks(limit=30):
    active_stocks = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    urls = [
        "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
        "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY_ALL?response=json"
    ]
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=6)
            data = res.json()
            rows = []
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict) and 'data' in data:
                fields = data.get('fields', [])
                for d in data['data']:
                    rows.append(dict(zip(fields, d)))
            if rows:
                for r in rows:
                    sym = str(r.get('Code', r.get('證券代號', ''))).strip()
                    name = str(r.get('Name', r.get('證券名稱', ''))).strip()
                    val_str = str(r.get('TradeValue', r.get('成交金額', '0'))).replace(',', '').strip()
                    vol_str = str(r.get('TradeVolume', r.get('成交股數', '0'))).replace(',', '').strip()
                    try:
                        trade_value = float(val_str) if val_str else 0.0
                        trade_vol = int(vol_str) if vol_str else 0
                    except ValueError:
                        continue
                    if len(sym) == 4 and not sym.startswith('00') and trade_value > 50000000:
                        active_stocks.append({
                            'symbol': sym, 'name': name,
                            'trade_value': trade_value, 'trade_vol': trade_vol
                        })
                if active_stocks:
                    break
        except Exception:
            continue
    if active_stocks:
        active_stocks.sort(key=lambda x: x['trade_value'], reverse=True)
        return active_stocks[:limit]
    fallback = []
    for item in config.CURATED_THEME_POOL[:limit]:
        fallback.append({
            'symbol': item[0], 'name': item[1],
            'trade_value': 1000000000.0, 'trade_vol': 5000000
        })
    return fallback

def get_stock_history(symbol, period='4mo'):
    """取得台股量價，優先判斷上櫃興櫃市場，避免終端機跳出 404"""
    sym_clean = str(symbol).strip()
    
    # 台灣生技、網通、設備等許多標的為上櫃/興櫃(如 6467, 6696, 3131, 3324, 6187)
    # 若為常見上櫃代碼開頭(3, 5, 6, 8)，優先查 .TWO，失敗再查 .TW
    if sym_clean.startswith(('3', '5', '6', '8')):
        candidate_suffixes = ['.TWO', '.TW']
    else:
        candidate_suffixes = ['.TW', '.TWO']
        
    df = pd.DataFrame()
    for suffix in candidate_suffixes:
        try:
            full_sym = f"{sym_clean}{suffix}"
            stock = yf.Ticker(full_sym)
            temp_df = stock.history(period=period, raise_errors=False)
            if not temp_df.empty and len(temp_df) >= 3:
                df = temp_df
                break
        except Exception:
            continue
            
    if not df.empty:
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        df['60MA'] = df['Close'].rolling(60).mean()
        df['Vol_MA5'] = df['Volume'].rolling(5).mean()
        df['Vol_MA20'] = df['Volume'].rolling(20).mean()
        std20 = df['Close'].rolling(20).std()
        df['BB_Upper'] = df['20MA'] + (std20 * 2)
        df['BB_Lower'] = df['20MA'] - (std20 * 2)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        df['RSI'] = 100 - (100 / (1 + rs))
        
    return df

def get_macro_overview():
    overview = {}
    for name, sym in config.MACRO_TICKERS.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period='5d')
            if len(hist) >= 2:
                close = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                pct = ((close - prev) / prev) * 100
                overview[name] = {'close': round(close, 2), 'pct': round(pct, 2), 'change': round(close - prev, 2)}
            else:
                overview[name] = {'close': 0.0, 'pct': 0.0, 'change': 0.0}
        except Exception:
            overview[name] = {'close': 0.0, 'pct': 0.0, 'change': 0.0}
    return overview

def get_institutional_investors_summary():
    try:
        url = "https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=6).json()
        if res.get('stat') == 'OK' and 'data' in res:
            data = res['data']
            foreign = int(data[3][3].replace(',', '')) / 100000000
            trust = int(data[2][3].replace(',', '')) / 100000000
            dealer = (int(data[0][3].replace(',', '')) + int(data[1][3].replace(',', ''))) / 100000000
            return {'外資': round(foreign, 2), '投信': round(trust, 2), '自營商': round(dealer, 2), '合計': round(foreign + trust + dealer, 2)}
    except Exception:
        pass
    return {'外資': 0.0, '投信': 0.0, '自營商': 0.0, '合計': 0.0}

def get_top_investment_trust_stocks(limit=30):
    stocks = {}
    headers = {'User-Agent': 'Mozilla/5.0'}
    today = datetime.now()
    for delta in range(9):
        query_date = today - timedelta(days=delta)
        if query_date.weekday() >= 5 and delta == 0:
            continue
        date_str = query_date.strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?response=json&date={date_str}"
        try:
            res = requests.get(url, headers=headers, timeout=5).json()
            if res.get('stat') == 'OK' and 'data' in res and len(res['data']) > 0:
                count = 0
                for row in res.get('data', []):
                    sym = str(row[0]).strip()
                    name = str(row[1]).strip()
                    net_buy_str = str(row[4]).replace(',', '').strip()
                    try:
                        net_buy = int(net_buy_str)
                    except ValueError:
                        continue
                    if len(sym) == 4 and not sym.startswith('00') and net_buy > 0:
                        stocks[sym] = {'name': name, 'trust_buy_vol': net_buy, 'date': query_date.strftime('%Y-%m-%d')}
                        count += 1
                        if count >= limit:
                            break
                if stocks:
                    break
        except Exception:
            continue
    return stocks

def get_stock_news(keyword, max_items=4):
    news_list = []
    try:
        url = f"https://news.google.com/rss/search?q={keyword}+台股+股票&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.content, features='xml')
        items = soup.findAll('item')[:max_items]
        for item in items:
            title = item.title.text
            link = item.link.text
            pub_date = item.pubDate.text[:16]
            news_list.append({'title': title, 'link': link, 'date': pub_date})
    except Exception:
        pass
    return news_list
