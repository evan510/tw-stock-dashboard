# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from data_engine import (
    get_stock_history,
    get_twse_market_active_stocks,
    get_top_investment_trust_stocks,
    get_stock_news,
    resolve_stock
)
import config

def evaluate_entry_status(df, last, prev):
    close = round(float(last['Close']), 2)
    prev_close = round(float(prev['Close']), 2)
    pct_change = round(((close - prev_close) / prev_close) * 100, 2)
    ma5 = float(last['5MA']) if pd.notnull(last['5MA']) else close
    ma10 = float(last['10MA']) if pd.notnull(last['10MA']) else close
    ma20 = float(last['20MA']) if pd.notnull(last['20MA']) else close
    vol = float(last['Volume'])
    vol_ma5 = float(last['Vol_MA5']) if pd.notnull(last['Vol_MA5']) else vol
    vol_ratio = round(vol / (vol_ma5 + 1e-9), 2)
    rsi = float(last['RSI']) if pd.notnull(last['RSI']) else 50.0
    bias_5ma = round(((close - ma5) / ma5) * 100, 2)
    bias_20ma = round(((close - ma20) / ma20) * 100, 2)
    stop_loss = round(min(ma20, float(df['Low'].iloc[-3:].min())), 2)
    
    if bias_5ma > 8.0 or bias_20ma > 20.0 or rsi > 80:
        return ("⚠️ 極度過熱 (切勿追高)", "red", f"短線急漲過猛（5MA正乖離達 {bias_5ma}%，RSI {round(rsi,1)}），隨時有獲利回吐震盪風險。建議等待拉回回測 5MA/10MA 守穩再進場！", stop_loss)
    elif close > ma20 and vol_ratio >= 1.35 and pct_change >= 2.0:
        return ("🟢 動能突破 (可以進場)", "green", f"帶量突破整理區（均量 {vol_ratio} 倍），均線發散多頭，可逢回測分批進場，停損嚴守今日低點 ${round(float(last['Low']), 2)}。", stop_loss)
    elif close > ma20 and abs(close - ma5) / ma5 <= 0.025 and vol < vol_ma5 * 1.1:
        return ("🟢 回測有守 (買點浮現)", "green", f"股價回測 5MA/10MA 不破，成交量良性萎縮（均量 {vol_ratio} 倍），浮額清洗完畢，屬風險報酬比極佳之切入點！", stop_loss)
    elif close > ma20:
        return ("🟡 區間整理 (觀望等待)", "orange", "站穩月線但動能尚未表態，處以盤代跌結構，建議列入觀察名單，等待帶量攻擊紅棒再行介入。", stop_loss)
    else:
        return ("🔴 弱勢破線 (嚴禁進場)", "gray", "跌破 20MA 生命線，短中期動能轉弱，上方套牢賣壓沉重，切忌盲目抄底，已有持股者逢反彈宜執行減碼。", stop_loss)

def analyze_dynamic_market_hot_stocks(limit=30):
    active_pool = get_twse_market_active_stocks(limit=limit)
    results = []
    for item in active_pool:
        sym = item['symbol']
        name = item['name']
        df = get_stock_history(sym, period='3mo')
        if df.empty or len(df) < 15:
            continue
        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = round(float(last['Close']), 2)
        pct_change = round(((close - float(prev['Close'])) / float(prev['Close'])) * 100, 2)
        vol = float(last['Volume'])
        vol_ma5 = float(last['Vol_MA5']) if pd.notnull(last['Vol_MA5']) else vol
        vol_ratio = round(vol / (vol_ma5 + 1e-9), 2)
        rsi = round(float(last['RSI']), 1) if pd.notnull(last['RSI']) else 50.0
        ma5 = round(float(last['5MA']), 2) if pd.notnull(last['5MA']) else close
        bias_5ma = round(((close - ma5) / ma5) * 100, 2)
        signal, color, advice, stop_loss = evaluate_entry_status(df, last, prev)
        turnover_billion = round(item.get('trade_value', 0) / 100000000, 2)
        results.append({
            'symbol': sym, 'name': name, 'close': close, 'pct_change': pct_change,
            'turnover_billion': turnover_billion, 'vol_ratio': vol_ratio, 'rsi': rsi,
            'bias_5ma': bias_5ma, 'entry_signal': signal, 'entry_color': color,
            'action_advice': advice, 'stop_loss': stop_loss
        })
    return results

def analyze_custom_pool_stocks(pool_list):
    results = []
    for item in pool_list:
        sym = item['symbol']
        name = item.get('name', sym)
        tag = item.get('tag', '自選')
        note = item.get('note', '')
        df = get_stock_history(sym, period='3mo')
        if df.empty or len(df) < 10:
            continue
        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = round(float(last['Close']), 2)
        pct_change = round(((close - float(prev['Close'])) / float(prev['Close'])) * 100, 2)
        vol = float(last['Volume'])
        vol_ma5 = float(last['Vol_MA5']) if pd.notnull(last['Vol_MA5']) else vol
        vol_ratio = round(vol / (vol_ma5 + 1e-9), 2)
        rsi = round(float(last['RSI']), 1) if pd.notnull(last['RSI']) else 50.0
        ma5 = round(float(last['5MA']), 2) if pd.notnull(last['5MA']) else close
        bias_5ma = round(((close - ma5) / ma5) * 100, 2)
        signal, color, advice, stop_loss = evaluate_entry_status(df, last, prev)
        results.append({
            'symbol': sym, 'name': name, 'tag': tag, 'note': note,
            'close': close, 'pct_change': pct_change, 'vol_ratio': vol_ratio,
            'rsi': rsi, 'bias_5ma': bias_5ma, 'entry_signal': signal,
            'entry_color': color, 'action_advice': advice, 'stop_loss': stop_loss
        })
    return results

def analyze_curated_theme_stocks():
    results = []
    for sym, name, theme in config.CURATED_THEME_POOL:
        df = get_stock_history(sym, period='3mo')
        if df.empty or len(df) < 15:
            continue
        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = round(float(last['Close']), 2)
        pct_change = round(((close - float(prev['Close'])) / float(prev['Close'])) * 100, 2)
        vol = float(last['Volume'])
        vol_ma5 = float(last['Vol_MA5']) if pd.notnull(last['Vol_MA5']) else vol
        vol_ratio = round(vol / (vol_ma5 + 1e-9), 2)
        rsi = round(float(last['RSI']), 1) if pd.notnull(last['RSI']) else 50.0
        ma5 = round(float(last['5MA']), 2) if pd.notnull(last['5MA']) else close
        bias_5ma = round(((close - ma5) / ma5) * 100, 2)
        signal, color, advice, stop_loss = evaluate_entry_status(df, last, prev)
        results.append({
            'symbol': sym, 'name': name, 'theme': theme, 'close': close,
            'pct_change': pct_change, 'vol_ratio': vol_ratio, 'rsi': rsi,
            'bias_5ma': bias_5ma, 'entry_signal': signal, 'entry_color': color,
            'action_advice': advice, 'stop_loss': stop_loss
        })
    results.sort(key=lambda x: x['vol_ratio'], reverse=True)
    return results

def run_ai_deep_analysis(query_input):
    sym, resolved_name = resolve_stock(query_input)
    if not sym:
        return None, "請輸入有效的股票名稱或代號！"
    df = get_stock_history(sym, period='4mo')
    if df.empty or len(df) < 15:
        return None, f"查無代號或名稱為『{query_input}』({sym}) 的歷史行情。"
    last = df.iloc[-1]
    prev = df.iloc[-2]
    close = round(float(last['Close']), 2)
    pct_change = round(((close - float(prev['Close'])) / float(prev['Close'])) * 100, 2)
    high_price = round(float(last['High']), 2)
    low_price = round(float(last['Low']), 2)
    ma5 = round(float(last['5MA']), 2) if pd.notnull(last['5MA']) else close
    ma10 = round(float(last['10MA']), 2) if pd.notnull(last['10MA']) else close
    ma20 = round(float(last['20MA']), 2) if pd.notnull(last['20MA']) else close
    ma60 = round(float(last['60MA']), 2) if pd.notnull(last['60MA']) else close
    vol = float(last['Volume'])
    vol_ma5 = float(last['Vol_MA5']) if pd.notnull(last['Vol_MA5']) else vol
    vol_ratio = round(vol / (vol_ma5 + 1e-9), 2)
    rsi = round(float(last['RSI']), 1) if pd.notnull(last['RSI']) else 50.0
    
    if vol_ratio >= 1.5 and pct_change >= 2.0:
        buying_power = "🔥 主力強攻掃貨（買盤動能極度充沛）"
        vol_structure = "典型帶量長紅攻擊型態，主力大戶積極進駐建倉，市場人氣聚集。"
    elif vol_ratio >= 1.5 and pct_change <= -2.0:
        buying_power = "⚠️ 高檔爆量長黑（賣盤沉重，主力獲利倒貨）"
        vol_structure = "出量收黑K棒，顯示高檔逢高調節賣壓出籠，短線提防假突破拉回震盪。"
    elif vol_ratio < 0.8:
        buying_power = "💤 縮量沈澱（買賣雙方觀望，浮額清洗中）"
        vol_structure = "量縮洗盤整理，若能在關鍵均線處止跌，往往醞釀下一波發動契機。"
    else:
        buying_power = "⚖️ 買賣勢均力敵（常態換手）"
        vol_structure = "成交量接近 5 日均量水準，多空雙方短線維持既有技術軌道行進。"
        
    if close > ma20 and ma5 > ma10 and ma10 > ma20 and vol_ratio >= 1.25 and rsi < 78:
        ai_verdict = "🟢 強烈建議波段進場（多方動能共振）"
        entry_zone = f"${round(close * 0.98, 1)} ~ ${close}"
        stop_loss = round(min(ma20, low_price * 0.98), 2)
        target = round(close * 1.12, 2)
    elif close > ma20 and abs(close - ma5) / ma5 <= 0.03:
        ai_verdict = "🟡 建議回測分批佈局（支撐有守）"
        entry_zone = f"${ma5} ~ ${round(ma5 * 1.015, 1)}"
        stop_loss = round(ma20 * 0.98, 2)
        target = round(close * 1.10, 2)
    elif rsi >= 78 or ((close - ma5) / ma5) > 0.08:
        ai_verdict = "⚠️ 觀望嚴禁追高（指標過熱，防震盪拉回）"
        entry_zone = "暫不建議市價追價，靜待回測 5MA 量縮再進場"
        stop_loss = round(ma5 * 0.97, 2)
        target = round(close * 1.06, 2)
    else:
        ai_verdict = "🔴 嚴禁介入 / 偏空防守（跌破關鍵生命線）"
        entry_zone = "不建議進場，手上有持股者逢反彈應執行減碼"
        stop_loss = round(close * 0.96, 2)
        target = round(ma20, 2)
        
    rr = round(max(target - close, 0.1) / max(close - stop_loss, 0.1), 1)
    news = get_stock_news(resolved_name, max_items=4)
    return {
        'symbol': sym, 'name': resolved_name, 'close': close, 'pct_change': pct_change,
        'high': high_price, 'low': low_price, 'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'ma60': ma60,
        'vol': vol, 'vol_ratio': vol_ratio, 'rsi': rsi, 'buying_power': buying_power,
        'vol_structure': vol_structure, 'ai_verdict': ai_verdict, 'entry_zone': entry_zone,
        'stop_loss': stop_loss, 'target': target, 'rr': rr, 'news': news
    }, None

def analyze_and_rank_pool(limit=30):
    candidates = get_top_investment_trust_stocks(limit=limit)
    rankings = []
    for symbol, meta in candidates.items():
        name = meta['name']
        trust_vol = meta.get('trust_buy_vol', 0)
        df = get_stock_history(symbol, period='3mo')
        if df.empty or len(df) < 20:
            continue
        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = round(float(last['Close']), 2)
        pct_change = round(((close - float(prev['Close'])) / float(prev['Close'])) * 100, 2)
        ma5 = round(float(last['5MA']), 2) if pd.notnull(last['5MA']) else close
        ma10 = round(float(last['10MA']), 2) if pd.notnull(last['10MA']) else close
        ma20 = round(float(last['20MA']), 2) if pd.notnull(last['20MA']) else close
        vol = float(last['Volume'])
        vol_ma5 = float(last['Vol_MA5']) if pd.notnull(last['Vol_MA5']) else vol
        rsi = round(float(last['RSI']), 1) if pd.notnull(last['RSI']) else 50.0
        score = 40
        signals, tags = [], []
        if trust_vol >= 1000:
            score += 20; signals.append(f"投信大舉重倉鎖碼：買超 {trust_vol:,} 張"); tags.append("投信重倉")
        elif trust_vol >= 300:
            score += 15; signals.append(f"投信積極建倉：買超 {trust_vol:,} 張"); tags.append("投信進駐")
        if close > ma20:
            score += 15; signals.append("站穩 20MA 生命線（多方確立）")
        else:
            score -= 25; signals.append("跌破 20MA 生命線（弱勢整理）")
        if ma5 > ma10 and ma10 > ma20:
            score += 15; signals.append("均線完美多頭排列 (5MA > 10MA > 20MA)"); tags.append("多頭排列")
        if vol > vol_ma5 * 1.3:
            score += 15; signals.append("出量攻擊：成交量高於 5 日均量 30%"); tags.append("放量突破")
        stop_loss = round(min(ma20, float(df['Low'].iloc[-3:].min())), 2)
        target_price = round(close * 1.12, 2)
        rr_ratio = round(max(target_price - close, 0.1) / max(close - stop_loss, 0.1), 1)
        rankings.append({
            'symbol': symbol, 'name': name, 'close': close, 'pct_change': pct_change,
            'trust_vol': trust_vol, 'score': min(max(score, 0), 100), 'ma20': ma20,
            'stop_loss': stop_loss, 'target_price': target_price, 'rr_ratio': rr_ratio,
            'signals': signals, 'tags': tags
        })
    rankings.sort(key=lambda x: x['score'], reverse=True)
    return rankings
