# -*- coding: utf-8 -*-
import logging
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import streamlit as st
import config

# 抑制 yfinance 終端報錯
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_online_stock_name(symbol):
    """當本地字典沒有時，自動向 Yahoo Finance / TWSE 抓取官方公司簡稱或 ETF 名稱"""
    sym_clean = str(symbol).strip().upper()
    
    # 常用 ETF / 特別股保底表
    fallback_map = {
        '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高股息',
        '00919': '群益台灣精選高息', '00929': '復華台灣科技優息', '006208': '富邦台50',
        '00940': '元大台灣價值高息', '00713': '元大台灣高息低波', '00679B': '元大美債20年',
        '00687B': '國泰20年美債'
    }
    if sym_clean in fallback_map:
        return fallback_map[sym_clean]
        
    suffixes = ['.TW', '.TWO'] if not sym_clean.startswith(('3', '4', '5', '6', '8')) else ['.TWO', '.TW']
    for s in suffixes:
        try:
            t = yf.Ticker(f"{sym_clean}{s}")
            name = t.info.get('shortName') or t.info.get('longName')
            if name:
                clean_name = name.split(' ')[0].replace('Co.,', '').replace('CORP.', '').replace('LIMITED', '').strip()
                return clean_name
        except Exception:
            continue
            
    return f"台股 {sym_clean}"

def resolve_stock(query_text):
    """
    全台股/ETF 雙向代號與名稱解析器
    支援 0050, 00878, 6467, 泰合, 仁新 等所有上市櫃與 ETF
    """
    clean = str(query_text).strip().upper()
    if not clean:
        return "", ""
        
    # 1. 精準命中字典 (名稱或代號)
    if clean in config.STOCK_NAME_MAP:
        mapped = config.STOCK_NAME_MAP[clean]
        # 若 clean 本身是數字或以 00 開頭的代號
        if clean.isdigit() or (clean.startswith('00') and len(clean) >= 4):
            return clean, mapped
        else:
            # clean 是中文名稱
            full_name = config.STOCK_NAME_MAP.get(mapped, clean)
            return mapped, full_name

    # 2. 模糊搜尋本地字典
    for name, sym in config.STOCK_NAME_MAP.items():
        if (clean in name or name in clean) and not (clean.isdigit() or sym.isdigit() and len(clean) == len(sym)):
            return sym, config.STOCK_NAME_MAP.get(sym, name)

    # 3. 若為純數字代碼（4~6碼）或含英數代號 (如 00679B) -> 自動聯網查中文全名
    is_code = (clean.isdigit() and 4 <= len(clean) <= 6) or (clean.startswith('00') and len(clean) >= 4)
    if is_code:
        online_name = fetch_online_stock_name(clean)
        return clean, online_name

    return clean, clean

@st.cache_data(ttl=900, show_spinner=False)
def get_stock_history(symbol, period='4mo'):
    """取得台股與 ETF 歷史量價，支援上市 .TW、上櫃/興櫃 .TWO 與 00878 等 ETF"""
    sym_clean = str(symbol).strip().upper()
    
    # 判斷優先查詢後綴
    if sym_clean.startswith(('3', '4', '5', '6', '8')) and not sym_clean.startswith(('00', '01')):
        candidate_suffixes = ['.TWO', '.TW']
    else:
        candidate_suffixes = ['.TW', '.TWO']
        
    df = pd.DataFrame()
    for suffix in candidate_suffixes:
        try:
            full_sym = f"{sym_clean}{suffix}"
            stock = yf.Ticker(full_sym)
            # 優先以傳入的 period 查詢
            temp_df = stock.history(period=period, raise_errors=False)
            
            # 若為 00878 等 ETF 在週末或盤後遇 period 回傳不足，自動以 1mo 備援
            if temp_df.empty or len(temp_df) < 1:
                temp_df = stock.history(period='1mo', raise_errors=False)
                
            if not temp_df.empty and len(temp_df) >= 1:
                df = temp_df
                break
        except Exception:
            continue
            
    if not df.empty:
        # 移除可能存在的空值或無效交易日
        df = df.dropna(subset=['Close'])
        
        # 均線系統 (加入 min_periods 確保即使天數較短也能算出均線，不致報錯)
        df['5MA'] = df['Close'].rolling(5, min_periods=1).mean()
        df['10MA'] = df['Close'].rolling(10, min_periods=1).mean()
        df['20MA'] = df['Close'].rolling(20, min_periods=1).mean()
        df['60MA'] = df['Close'].rolling(60, min_periods=1).mean()
        df['Vol_MA5'] = df['Volume'].rolling(5, min_periods=1).mean()
        df['Vol_MA20'] = df['Volume'].rolling(20, min_periods=1).mean()
        
        # 布林通道 (20MA +- 2標準差)
        std20 = df['Close'].rolling(20, min_periods=2).std().fillna(0)
        df['BB_Upper'] = df['20MA'] + (std20 * 2)
        df['BB_Lower'] = df['20MA'] - (std20 * 2)
        
        # RSI (14日)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
        rs = gain / (loss + 1e-9)
        df['RSI'] = 100 - (100 / (1 + rs))
        df['RSI'] = df['RSI'].fillna(50.0)
        
    return df

@st.cache_data(ttl=900, show_spinner=False)
def get_twse_market_active_stocks(limit=30):
    active_stocks = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    urls = [
        "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
        "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY_ALL?response=json"
    ]
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code != 200:
                continue
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
                    # 允許 4~5 碼股票與主流 ETF
                    if (len(sym) == 4 or sym.startswith('00')) and trade_value > 50000000:
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

@st.cache_data(ttl=900, show_spinner=False)
def get_macro_overview():
    overview = {}
    for name, sym in config.MACRO_TICKERS.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period='5d', raise_errors=False)
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

@st.cache_data(ttl=900, show_spinner=False)
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

@st.cache_data(ttl=900, show_spinner=False)
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
                    if (len(sym) == 4 or sym.startswith('00')) and net_buy > 0:
                        stocks[sym] = {'name': name, 'trust_buy_vol': net_buy, 'date': query_date.strftime('%Y-%m-%d')}
                        count += 1
                        if count >= limit:
                            break
                if stocks:
                    break
        except Exception:
            continue
    return stocks

@st.cache_data(ttl=1800, show_spinner=False)
def get_stock_news(keyword, max_items=4):
    news_list = []
    try:
        url = f"https://news.google.com/rss/search?q={keyword}+台股+股票&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            try:
                soup = BeautifulSoup(res.content, features='xml')
            except Exception:
                soup = BeautifulSoup(res.content, features='html.parser')
            items = soup.findAll('item')[:max_items]
            for item in items:
                title = item.title.text if item.title else ""
                link = item.link.text if item.link else ""
                pub_date = item.pubDate.text[:16] if item.pubDate else ""
                if title:
                    news_list.append({'title': title, 'link': link, 'date': pub_date})
    except Exception:
        pass
    return news_list

@st.cache_data(ttl=900, show_spinner=False)
def get_institutional_streak_stocks(limit=30):
    """
    獲取近期外資、投信連續加碼買超清單，並標記『投信連買』、『土洋合買』籌碼特徵
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    today = datetime.now()
    
    # 讀取近數個交易日投信買超日報
    valid_dates = []
    for delta in range(12):
        d = today - timedelta(days=delta)
        if d.weekday() < 5:
            valid_dates.append(d)
        if len(valid_dates) >= 4:
            break
            
    day_buys = []
    for q_date in valid_dates:
        date_str = q_date.strftime('%Y%m%d')
        url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?response=json&date={date_str}"
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                res_json = res.json()
                data_rows = res_json.get('data', [])
                if res_json.get('stat') == 'OK' and data_rows:
                    daily_map = {}
                    for row in data_rows:
                        if len(row) < 6:
                            continue
                        sym = str(row[1]).strip()
                        name = str(row[2]).strip()
                        # row[5] 為買賣超張數（千股/張）
                        net_buy_str = str(row[5]).replace(',', '').strip()
                        try:
                            net_buy = int(net_buy_str)
                            if net_buy > 0 and (len(sym) == 4 or sym.startswith('00')):
                                daily_map[sym] = {'name': name, 'buy': net_buy}
                        except ValueError:
                            continue
                    if daily_map:
                        day_buys.append(daily_map)
        except Exception:
            continue
            
    results = {}
    if day_buys:
        latest_day = day_buys[0]
        # 1. 優先比對連買 2 天以上者
        for sym, meta in latest_day.items():
            streak_count = 1
            total_vol = meta['buy']
            for past_day in day_buys[1:]:
                if sym in past_day:
                    streak_count += 1
                    total_vol += past_day[sym]['buy']
                else:
                    break
            
            if streak_count >= 2:
                results[sym] = {
                    'name': meta['name'],
                    'streak_days': streak_count,
                    'latest_buy_vol': meta['buy'],
                    'total_streak_vol': total_vol,
                    'streak_type': '🔥 投信波段認養' if streak_count >= 3 else '⚡ 投信連買突擊'
                }
                if len(results) >= limit:
                    break
                    
        # 2. 若連買家數未滿 limit，自動以最新單日大額買超前幾名補足
        if len(results) < limit:
            sorted_by_buy = sorted(latest_day.items(), key=lambda x: x[1]['buy'], reverse=True)
            for sym, meta in sorted_by_buy:
                if sym not in results and meta['buy'] >= 500:
                    results[sym] = {
                        'name': meta['name'],
                        'streak_days': 1,
                        'latest_buy_vol': meta['buy'],
                        'total_streak_vol': meta['buy'],
                        'streak_type': '🚀 單日投信爆量急敲'
                    }
                if len(results) >= limit:
                    break

    # 3. 若證交所週末或非交易時間連線空缺，自動啟用投信重倉名單保底
    if not results:
        fallback_trust = get_top_investment_trust_stocks(limit=limit)
        for sym, meta in fallback_trust.items():
            results[sym] = {
                'name': meta['name'],
                'streak_days': 2,
                'latest_buy_vol': meta.get('trust_buy_vol', 800),
                'total_streak_vol': meta.get('trust_buy_vol', 800) * 2,
                'streak_type': '🎯 投信鎖碼焦點'
            }
            if len(results) >= limit:
                break

    return results

@st.cache_data(ttl=600, show_spinner=False)
def scan_theme_catalyst_news(theme_category="全部題材", max_news=10):
    """
    掃描全市場重大財經題材催化劑新聞，支援自選主題分類
    """
    theme_keywords_map = {
        "全部題材": [
            "CoWoS 擴產", "CPO 矽光子", "水冷散熱 伺服器", "重電 強韌電網",
            "生技 拆股 授權", "無人機 軍工", "營收 創新高 雙增"
        ],
        "CPO 矽光子 / CoWoS": ["CPO 矽光子", "CoWoS 先進封裝", "光通訊 800G"],
        "水冷散熱 / AI 伺服器": ["水冷散熱 伺服器", "B200 GB200 出貨", "機櫃散熱 雙鴻 奇鋐"],
        "重電綠能 / 強韌電網": ["重電 強韌電網", "台電 變壓器", "綠能 儲能 華城 中興電"],
        "生技新藥 / 拆股授權": ["生技 解盲 授權", "泰合生技 仁新 拆股", "新藥 藥華藥 保瑞 美時"],
        "無人機 / 國防軍工": ["無人機 軍工", "國防 航太 雷虎", "軍工 標案 漢翔"],
        "營收新高 / 法人雙增": ["營收 創新高 雙增", "獲利 季增 年增", "外資 投信 升評"]
    }
    
    keywords = theme_keywords_map.get(theme_category, theme_keywords_map["全部題材"])
    catalyst_news = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for kw in keywords:
        try:
            query = f"{kw}+台股"
            url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
            res = requests.get(url, headers=headers, timeout=4)
            if res.status_code == 200:
                try:
                    soup = BeautifulSoup(res.content, features='xml')
                except Exception:
                    soup = BeautifulSoup(res.content, features='html.parser')
                items = soup.findAll('item')[:3]
                for item in items:
                    title = item.title.text if item.title else ""
                    link = item.link.text if item.link else ""
                    pub_date = item.pubDate.text[:16] if item.pubDate else ""
                    if title:
                        catalyst_news.append({
                            'tag': kw.split(' ')[0],
                            'title': title,
                            'link': link,
                            'date': pub_date
                        })
        except Exception:
            continue
        if len(catalyst_news) >= max_news * 2:
            break
            
    # 去重
    seen_titles = set()
    unique_news = []
    for n in catalyst_news:
        if n['title'] not in seen_titles:
            seen_titles.add(n['title'])
            unique_news.append(n)
            
    return unique_news[:max_news]

