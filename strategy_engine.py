# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import streamlit as st
import data_engine
from data_engine import (
    get_stock_history,
    get_twse_market_active_stocks,
    get_top_investment_trust_stocks,
    get_stock_news,
    resolve_stock
)
get_institutional_streak_stocks = getattr(data_engine, 'get_institutional_streak_stocks', lambda limit=30: {})
scan_theme_catalyst_news = getattr(data_engine, 'scan_theme_catalyst_news', lambda theme_category="全部題材", max_news=10: [])
get_stock_institutional_breakdown = getattr(data_engine, 'get_stock_institutional_breakdown', lambda sym: {'has_data': False})
from custom_pool_manager import load_custom_pool
import config

def generate_sparkline(series):
    """
    產生純文字火花走勢縮圖 (Sparkline:  ▂▃▅▆▇)
    """
    if series is None or len(series) < 2:
        return "───"
    vals = [float(v) for v in series if pd.notnull(v)]
    if len(vals) < 2:
        return "───"
    min_v, max_v = min(vals), max(vals)
    if max_v == min_v:
        return "▅▅▅▅▅"
    ticks = [' ', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    spark = ""
    for v in vals:
        idx = int(((v - min_v) / (max_v - min_v + 1e-9)) * (len(ticks) - 1))
        idx = min(max(idx, 0), len(ticks) - 1)
        spark += ticks[idx]
    return spark

@st.cache_data(ttl=300, show_spinner=False)
def get_intraday_volume_surge_radar(limit=20):
    """
    ⚡ 盤中早盤預估成交量起漲雷達
    根據台股盤中時間動態推估今日全天成交量，鎖定【預估放量 >= 1.5倍】且【漲幅 +1.5% ~ +5.5%】起漲焦點！
    """
    from datetime import datetime
    now = datetime.now()
    cur_hour = now.hour
    cur_min = now.minute
    
    # 計算開盤已過分鐘數 (09:00 開盤至 13:30 收盤，共 270 分鐘)
    if cur_hour < 9:
        elapsed_minutes = 15  # 尚未開盤時預設依早盤模擬
    elif cur_hour > 13 or (cur_hour == 13 and cur_min >= 30):
        elapsed_minutes = 270  # 已收盤，全日量
    else:
        elapsed_minutes = max((cur_hour - 9) * 60 + cur_min, 15)
        
    # 台股歷史累積成交量曲線權重：前15分鐘約佔18%，前30分鐘約佔28%，前60分鐘約佔42%
    if elapsed_minutes <= 15:
        expected_ratio = 0.18
    elif elapsed_minutes <= 30:
        expected_ratio = 0.28
    elif elapsed_minutes <= 60:
        expected_ratio = 0.42
    elif elapsed_minutes <= 120:
        expected_ratio = 0.65
    else:
        expected_ratio = min(elapsed_minutes / 270.0, 1.0)
        
    active_stocks = get_twse_market_active_stocks(limit=50)
    radar_picks = []
    
    for s in active_stocks:
        sym = s['symbol']
        name = s['name']
        df = get_stock_history(sym, period='2mo')
        if df.empty or len(df) < 5:
            continue
            
        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = round(float(last['Close']), 2)
        prev_close = float(prev['Close'])
        pct_change = round(((close - prev_close) / (prev_close + 1e-9)) * 100, 2)
        
        cur_vol = float(last['Volume'])
        vol_ma20 = float(last['Vol_MA20']) if ('Vol_MA20' in last and pd.notnull(last['Vol_MA20'])) else cur_vol
        ma5 = float(last['5MA']) if ('5MA' in last and pd.notnull(last['5MA'])) else close
        
        # 預估全天成交量 (Projected Volume)
        projected_vol = round(cur_vol / max(expected_ratio, 0.15), 0)
        projected_vol_ratio = round(projected_vol / (vol_ma20 + 1e-9), 2)
        
        # 篩選起漲點條件：漲幅 +1.5% ~ +6.5%，預估量 >= 1.35 倍均量，站上 5MA
        if 1.5 <= pct_change <= 7.0 and projected_vol_ratio >= 1.35 and close >= ma5:
            radar_picks.append({
                'symbol': sym,
                'name': name,
                'close': close,
                'pct_change': pct_change,
                'projected_vol_ratio': projected_vol_ratio,
                'cur_vol': cur_vol,
                'projected_vol': projected_vol,
                'surge_signal': '🔥 早盤爆量起漲突擊' if projected_vol_ratio >= 2.0 else '⚡ 預估放量突破',
                'entry_advice': f"早盤預估全日量將達均量 {projected_vol_ratio} 倍，動能剛起跑，沿 5MA 順勢佈局！"
            })
            
    radar_picks.sort(key=lambda x: x['projected_vol_ratio'], reverse=True)
    return radar_picks[:limit]

# ================= 1. 大盤體質評分 (Market Regime Score) =================
@st.cache_data(ttl=600, show_spinner=False)
def calculate_market_regime():
    twii_df = get_stock_history('^TWII', period='4mo')
    twoii_df = get_stock_history('^TWOII', period='4mo')
    
    if twii_df.empty or len(twii_df) < 15:
        return {'score': 55, 'status': '🟡 NEUTRAL (震盪偏多)', 'color': 'orange', 'desc': '大盤處於均線整理區間，嚴格控管短線停損。', 'twii_pct20': 0.0}
        
    last = twii_df.iloc[-1]
    close = float(last['Close'])
    ma5 = float(last['5MA']) if pd.notnull(last['5MA']) else close
    ma20 = float(last['20MA']) if pd.notnull(last['20MA']) else close
    ma60 = float(last['60MA']) if pd.notnull(last['60MA']) else close
    vol = float(last['Volume'])
    vol_ma20 = float(last['Vol_MA20']) if pd.notnull(last['Vol_MA20']) else vol
    
    score = 0
    if close > ma5: score += 10
    if close > ma20: score += 15
    if close > ma60: score += 5
    if ma5 > ma20: score += 15
    if ma20 > ma60: score += 10
    if vol >= vol_ma20 * 1.0: score += 15
    if vol >= vol_ma20 * 1.2: score += 10
    
    if not twoii_df.empty and len(twoii_df) >= 5:
        otc_last = twoii_df.iloc[-1]
        otc_close = float(otc_last['Close'])
        otc_ma20 = float(otc_last['20MA']) if pd.notnull(otc_last['20MA']) else otc_close
        if otc_close > otc_ma20: score += 20
        
    score = min(max(score, 0), 100)
    
    p20_close = float(twii_df['Close'].iloc[-21]) if len(twii_df) >= 21 else float(twii_df['Close'].iloc[0])
    twii_pct20 = round(((close - p20_close) / p20_close) * 100, 2)
    
    if score >= 75:
        status, color = "🟢 BULLISH (強勢多頭)", "green"
        desc = "大盤均線多頭發散且量能充足，允許全力啟動短線突破策略。"
    elif score >= 40:
        status, color = "🟡 NEUTRAL (區間震盪)", "orange"
        desc = "大盤處於均線震盪期，嚴選強於大盤領頭羊，提防假突破。"
    else:
        status, color = "🔴 BEARISH (空頭防守)", "red"
        desc = "大盤評分低於 40 分風控警戒線，全系統強制啟動保護：禁止發出 BUY 訊號！"
        
    return {'score': score, 'status': status, 'color': color, 'desc': desc, 'twii_pct20': twii_pct20}

# ================= 2. 規格書核心評估 (Breakout / Pre-Breakout / Too Extended) =================
def evaluate_entry_status(df, last, prev, market_score=60, twii_pct20=0.0):
    close = round(float(last['Close']), 2)
    prev_close = round(float(prev['Close']), 2)
    pct_change = round(((close - prev_close) / prev_close) * 100, 2)
    
    ma5 = float(last['5MA']) if pd.notnull(last['5MA']) else close
    ma10 = float(last['10MA']) if pd.notnull(last['10MA']) else close
    ma20 = float(last['20MA']) if pd.notnull(last['20MA']) else close
    vol = float(last['Volume'])
    vol_ma20 = float(last['Vol_MA20']) if pd.notnull(last['Vol_MA20']) else vol
    vol_ratio = round(vol / (vol_ma20 + 1e-9), 2)
    rsi = float(last['RSI']) if pd.notnull(last['RSI']) else 50.0
    bias_5ma = round(((close - ma5) / ma5) * 100, 2)
    stop_loss = round(min(ma20, float(df['Low'].iloc[-3:].min())), 2)
    
    p20_close = float(df['Close'].iloc[-21]) if len(df) >= 21 else float(df['Close'].iloc[0])
    stock_pct20 = round(((close - p20_close) / p20_close) * 100, 2)
    rs_factor = round(stock_pct20 - twii_pct20, 2)
    
    prev_20d_high = round(float(df['High'].iloc[-21:-1].max()), 2) if len(df) >= 21 else float(last['High'])
    
    risk_unit = max(round(close - stop_loss, 2), 0.2)
    target1 = round(close + (risk_unit * 1.0), 2)
    target2 = round(close + (risk_unit * 2.0), 2)
    rr1 = round((target1 - close) / risk_unit, 1)
    rr2 = round((target2 - close) / risk_unit, 1)
    
    pattern = "常態整理"
    if close >= prev_20d_high and vol_ratio >= 1.5:
        pattern = "🚀 20日放量突破"
    elif close > ma20 and abs(close - prev_20d_high) / (prev_20d_high + 1e-9) <= 0.025:
        pattern = "🎯 突破前夕窄幅蓄勢"
        
    if market_score < 40:
        return ("🟡 觀望等待 (大盤偏空鎖定)", "neutral", "大盤體質評分低於 40 分，風控啟動，全域禁止開倉。", stop_loss, target1, target2, rr1, rr2, rs_factor, pattern)
    
    if pct_change >= 7.0 or (prev_20d_high > 0 and close > prev_20d_high * 1.035) or bias_5ma > 8.5 or rsi > 80:
        return ("⚠️ 過度延伸 (TOO EXTENDED)", "hot", f"短線急漲過度延伸（漲幅 {pct_change}%，乖離過大），嚴禁追高！耐心等待拉回守穩再進。", stop_loss, target1, target2, rr1, rr2, rs_factor, "⚠️ 短線急漲過熱")
        
    if pattern == "🚀 20日放量突破" and close > ma20:
        return ("🟢 20日放量突破 (BUY)", "buy", f"放量突破 20 日高點 ${prev_20d_high}（均量 {vol_ratio} 倍），動能強烈，可於突破點附近分批進場！", stop_loss, target1, target2, rr1, rr2, rs_factor, pattern)
        
    if pattern == "🎯 突破前夕窄幅蓄勢" and vol < vol_ma20 * 1.1:
        return ("🟢 蓄勢即將突破 (BUY)", "buy", f"緊貼 20 日高點 ${prev_20d_high} 壓縮量縮整理，籌碼沈澱乾淨，盈虧比極佳，伏擊買點浮現！", stop_loss, target1, target2, rr1, rr2, rs_factor, pattern)
        
    if close > ma20:
        return ("🟡 區間蓄勢 (WATCH)", "neutral", "站穩月線但動能尚未表態，處以盤代跌結構，列入觀察名單。", stop_loss, target1, target2, rr1, rr2, rs_factor, pattern)
    else:
        return ("🔴 破線轉弱 (AVOID)", "bear", "跌破 20MA 生命線，動能偏弱，切忌盲目抄底，手中持股宜減碼。", stop_loss, target1, target2, rr1, rr2, rs_factor, "破線偏空")

# ================= 3. 老王均線獨門戰法引擎 =================
@st.cache_data(ttl=900, show_spinner=False)
def evaluate_oldwang_strategy(sym):
    df = get_stock_history(sym, period='4mo')
    if df.empty or len(df) < 20:
        return None
        
    last = df.iloc[-1]
    prev = df.iloc[-2]
    close = round(float(last['Close']), 2)
    open_p = round(float(last['Open']), 2)
    pct_change = round(((close - float(prev['Close'])) / float(prev['Close'])) * 100, 2)
    
    ma5 = round(float(last['5MA']), 2)
    ma10 = round(float(last['10MA']), 2)
    ma20 = round(float(last['20MA']), 2)
    ma60 = round(float(last['60MA']), 2)
    vol = float(last['Volume'])
    vol_ma5 = float(last['Vol_MA5'])
    
    recent_len = min(20, len(df))
    recent_20 = df.iloc[-recent_len:]
    if not recent_20.empty and 'Volume' in recent_20 and recent_20['Volume'].max() > 0:
        max_vol_idx = recent_20['Volume'].idxmax()
        max_vol_k_low = round(float(df.loc[max_vol_idx, 'Low']), 2)
        try:
            max_vol_k_date = max_vol_idx.strftime('%m/%d')
        except Exception:
            max_vol_k_date = str(max_vol_idx)
    else:
        max_vol_k_low = round(float(last['Low']), 2)
        max_vol_k_date = "近期"
    
    is_wan_li = (close > ma5) and (close > ma10) and (close > ma20) and (ma5 >= ma10 >= ma20)
    is_wu_yun = (close < ma5) and (close < ma10) and (close < ma20)
    
    if is_wan_li:
        cloud_status = "🟢 萬里無雲 (三陽開泰)"
        cloud_desc = "股價同時站穩 5MA、10MA、20MA 之上且均線多頭發散，上檔萬里無雲無壓力！"
    elif is_wu_yun:
        cloud_status = "🔴 烏雲密布 (三聲無奈)"
        cloud_desc = "跌破 5MA、10MA、20MA 所有均線，老王金律：下方無支撐，現金為王絕不抄底！"
    else:
        cloud_status = "🟡 糾結震盪 (均線整理)"
        cloud_desc = "均線糾結互有上下，等待放量突破或回測支撐表態。"
        
    is_black_k = close < open_p
    tested_support = (abs(close - ma5) / ma5 <= 0.015) or (abs(close - ma10) / ma10 <= 0.015)
    kept_ma = (close >= ma5 * 0.99) or (close >= ma10 * 0.99)
    vol_shrunk = vol < vol_ma5 * 1.1
    
    is_buy_black = is_black_k and tested_support and kept_ma and vol_shrunk and (close > ma20)
    
    exit_alert = "🟢 均線健全，順勢抱緊"
    if close < ma20:
        exit_alert = "🛑 【跌破 20MA 生命線】波段趨勢瓦解，老王金律：全數清倉，現金為王！"
    elif close < ma10:
        exit_alert = "🛑 【跌破 10MA 支撐】轉弱訊號，波段多單建議全數出場或嚴格防守！"
    elif close < ma5:
        exit_alert = "⚠️ 【跌破 5MA 短線線】強勢動能停滯，老王紀律：先賣一半減碼，落袋為安！"
    elif close < max_vol_k_low:
        exit_alert = f"💣 【跌破大量K低點 ${max_vol_k_low}】主力籌碼全數套牢，凶多吉少快撤退！"
        
    return {
        'symbol': sym, 'close': close, 'pct_change': pct_change,
        'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'ma60': ma60,
        'cloud_status': cloud_status, 'cloud_desc': cloud_desc,
        'is_wan_li': is_wan_li, 'is_buy_black': is_buy_black,
        'exit_alert': exit_alert, 'max_vol_low': max_vol_k_low, 'max_vol_date': max_vol_k_date,
        'vol_shrunk': vol_shrunk
    }

# ================= 4. 單檔與池分析 =================
@st.cache_data(ttl=900, show_spinner=False)
def analyze_single_stock_metrics(sym, market_score=60, twii_pct20=0.0):
    df = get_stock_history(sym, period='4mo')
    if df.empty or len(df) < 10:
        return None
    last = df.iloc[-1]
    prev = df.iloc[-2]
    close = round(float(last['Close']), 2)
    pct_change = round(((close - float(prev['Close'])) / float(prev['Close'])) * 100, 2)
    vol = float(last['Volume'])
    vol_ma20 = float(last['Vol_MA20']) if pd.notnull(last['Vol_MA20']) else vol
    vol_ratio = round(vol / (vol_ma20 + 1e-9), 2)
    rsi = round(float(last['RSI']), 1) if pd.notnull(last['RSI']) else 50.0
    ma5 = round(float(last['5MA']), 2) if pd.notnull(last['5MA']) else close
    bias_5ma = round(((close - ma5) / ma5) * 100, 2)
    
    signal, color, advice, stop_loss, t1, t2, rr1, rr2, rs, pattern = evaluate_entry_status(
        df, last, prev, market_score, twii_pct20
    )
    
    return {
        'close': close, 'pct_change': pct_change, 'vol_ratio': vol_ratio,
        'rsi': rsi, 'bias_5ma': bias_5ma, 'entry_signal': signal,
        'entry_color': color, 'action_advice': advice, 'stop_loss': stop_loss,
        'target1': t1, 'target2': t2, 'rr1': rr1, 'rr2': rr2, 'rs_factor': rs,
        'pattern': pattern, 'sparkline': generate_sparkline(df['Close'].iloc[-10:])
    }

def analyze_custom_pool_stocks(pool_list):
    regime = calculate_market_regime()
    results = []
    for item in pool_list:
        sym = item['symbol']
        r_sym, r_name = resolve_stock(sym)
        name = item.get('name') or r_name
        tag = item.get('tag', '自選')
        note = item.get('note', '')
        
        metrics = analyze_single_stock_metrics(r_sym, regime['score'], regime['twii_pct20'])
        if not metrics:
            continue
            
        results.append({'symbol': r_sym, 'name': name, 'tag': tag, 'note': note, **metrics})
    return results

@st.cache_data(ttl=900, show_spinner=False)
def analyze_dynamic_market_hot_stocks(limit=30):
    regime = calculate_market_regime()
    active_pool = get_twse_market_active_stocks(limit=limit)
    results = []
    for item in active_pool:
        sym = item['symbol']
        name = item['name']
        metrics = analyze_single_stock_metrics(sym, regime['score'], regime['twii_pct20'])
        if not metrics:
            continue
        turnover_billion = round(item.get('trade_value', 0) / 100000000, 2)
        results.append({'symbol': sym, 'name': name, 'turnover_billion': turnover_billion, **metrics})
    return results

@st.cache_data(ttl=900, show_spinner=False)
def analyze_curated_theme_stocks():
    regime = calculate_market_regime()
    results = []
    for sym, name, theme in config.CURATED_THEME_POOL:
        metrics = analyze_single_stock_metrics(sym, regime['score'], regime['twii_pct20'])
        if not metrics:
            continue
        results.append({'symbol': sym, 'name': name, 'theme': theme, **metrics})
    results.sort(key=lambda x: x['vol_ratio'], reverse=True)
    return results

def run_ai_deep_analysis(query_input):
    regime = calculate_market_regime()
    sym, resolved_name = resolve_stock(query_input)
    if not sym:
        return None, "請輸入有效的股票名稱、ETF 或代號！"
    df = get_stock_history(sym, period='4mo')
    if df.empty or len(df) < 10:
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
    vol_ma20 = float(last['Vol_MA20']) if pd.notnull(last['Vol_MA20']) else vol
    vol_ratio = round(vol / (vol_ma20 + 1e-9), 2)
    rsi = round(float(last['RSI']), 1) if pd.notnull(last['RSI']) else 50.0
    
    signal, color, advice, stop_loss, t1, t2, rr1, rr2, rs, pattern = evaluate_entry_status(
        df, last, prev, regime['score'], regime['twii_pct20']
    )
    
    # --- AI 深度多維度綜合診斷評分系統 (0 ~ 100 分) ---
    ai_score = 50
    diagnosis_tags = []
    
    # 1. 均線位階與多空型態 (30分)
    if close > ma20:
        ai_score += 15
        diagnosis_tags.append("月線生命線多頭")
    else:
        ai_score -= 20
        diagnosis_tags.append("月線破線偏空")
        
    if ma5 > ma10 and ma10 > ma20:
        ai_score += 15
        diagnosis_tags.append("短期均線多頭排列")
    elif ma5 < ma10 and ma10 < ma20:
        ai_score -= 15
        diagnosis_tags.append("短期均線空頭排列")
        
    # 2. 量能與主力攻擊 (25分)
    if vol_ratio >= 1.5 and pct_change > 0:
        ai_score += 15
        diagnosis_tags.append("放量攻擊")
    elif vol_ratio >= 1.5 and pct_change < 0:
        ai_score -= 15
        diagnosis_tags.append("爆量調節")
    elif vol_ratio < 0.7:
        diagnosis_tags.append("量縮沈澱")
        
    # 3. RS 相對大盤強度 (20分)
    if rs > 5.0:
        ai_score += 15
        diagnosis_tags.append("強於大盤(領頭羊)")
    elif rs < -5.0:
        ai_score -= 15
        diagnosis_tags.append("弱於大盤(落後股)")
        
    # 4. RSI 指標位階 (15分)
    if 50 <= rsi <= 72:
        ai_score += 10
        diagnosis_tags.append("RSI強勢黃金區")
    elif rsi > 78:
        ai_score -= 5
        diagnosis_tags.append("短線指標過熱")
    elif rsi < 35:
        ai_score -= 10
        diagnosis_tags.append("指標超跌弱勢")
        
    # 5. 老王戰法加分
    oldwang_metrics = evaluate_oldwang_strategy(sym)
    if oldwang_metrics:
        if oldwang_metrics.get('is_wan_li'):
            ai_score += 10
            diagnosis_tags.append("老王萬里無雲")
        if oldwang_metrics.get('is_buy_black'):
            ai_score += 10
            diagnosis_tags.append("老王買黑不買紅點")

    ai_score = int(min(max(ai_score, 10), 99))
    
    # 操盤訊號燈號判定 (action_signal)
    if "TOO EXTENDED" in signal or "過度延伸" in signal or rsi > 80:
        action_signal = "⚠️ 過熱警戒 (嚴禁追高 / 分批停利)"
        signal_color = "#f59e0b"
        signal_bg = "rgba(245, 158, 11, 0.15)"
        signal_badge = "OVEREXTENDED"
    elif "BUY" in signal or (close > ma20 and vol_ratio >= 1.3 and pct_change >= 1.5):
        action_signal = "🟢 建議買進 (動能浮現 / 順勢介入)"
        signal_color = "#22c55e"
        signal_bg = "rgba(34, 197, 94, 0.15)"
        signal_badge = "STRONG BUY"
    elif close < ma20 or "AVOID" in signal:
        action_signal = "🔴 建議賣出 (跌破防守 / 避開弱勢)"
        signal_color = "#ef4444"
        signal_bg = "rgba(239, 68, 68, 0.15)"
        signal_badge = "SELL / EXIT"
    else:
        action_signal = "🟡 觀望蓄勢 (多空拉鋸 / 等待表態)"
        signal_color = "#3b82f6"
        signal_bg = "rgba(59, 130, 246, 0.15)"
        signal_badge = "NEUTRAL / WATCH"
        
    # 自動合成 AI 深度操盤講評
    ai_analysis_narrative = f"【AI 量化深度評析】\n"
    ai_analysis_narrative += f"• 當前綜合技術體質評分為 {ai_score} 分，市場行動燈號為「{action_signal}」。\n"
    if close > ma20:
        ai_analysis_narrative += f"• 股價站穩 20MA 生命線 (${ma20}) 之上，短中期架構偏多，若量能持續放大則具向上攻堅動能。"
    else:
        ai_analysis_narrative += f"• 股價失守 20MA 生命線 (${ma20})，短線轉為空方控盤，技術面有測底疑慮，不宜過早抄底。"
    if vol_ratio >= 1.5:
        ai_analysis_narrative += f"今日成交量顯著放大至均量的 {vol_ratio} 倍，籌碼交換頻繁。"
    elif vol_ratio < 0.7:
        ai_analysis_narrative += f"成交量急縮（僅均量 {vol_ratio} 倍），浮額正在沉澱，耐心靜待突破起漲點。"
    if rs > 0:
        ai_analysis_narrative += f" 相對加權指數強勢 (+{rs}%)，具備主流股特質。"
    else:
        ai_analysis_narrative += f" 相對加權指數落後 ({rs}%)，需留意大盤拉回時的補跌風險。"

    if vol_ratio >= 1.5 and pct_change >= 2.0:
        buying_power = "🔥 主力強攻掃貨（短線動能極度充沛）"
        vol_structure = "突破長紅攻擊型態，短線量能噴發，市場關注度頂峰。"
    elif vol_ratio >= 1.5 and pct_change <= -2.0:
        buying_power = "⚠️ 出量長黑倒貨（獲利調節賣壓出籠）"
        vol_structure = "爆量收黑K棒，籌碼鬆動，短線慎防假突破拉回。"
    elif vol_ratio < 0.8:
        buying_power = "💤 縮量沈澱（浮額清洗整理中）"
        vol_structure = "極度量縮整理，往往醞釀下一波變盤表態契機。"
    else:
        buying_power = "⚖️ 換手常態（區間運行）"
        vol_structure = "成交量接近 20 日均量，技術指標維持常態。"
        
    news = get_stock_news(resolved_name, max_items=4)
    inst_breakdown = get_stock_institutional_breakdown(sym)
    sparkline_10d = generate_sparkline(df['Close'].iloc[-10:])
    
    return {
        'symbol': sym, 'name': resolved_name, 'close': close, 'pct_change': pct_change,
        'high': high_price, 'low': low_price, 'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'ma60': ma60,
        'vol': vol, 'vol_ratio': vol_ratio, 'rsi': rsi, 'buying_power': buying_power,
        'vol_structure': vol_structure, 'ai_verdict': signal, 'action_signal': action_signal,
        'signal_color': signal_color, 'signal_bg': signal_bg, 'signal_badge': signal_badge,
        'ai_score': ai_score, 'diagnosis_tags': diagnosis_tags, 'ai_narrative': ai_analysis_narrative,
        'entry_zone': f"${round(close * 0.99, 1)} ~ ${close}",
        'stop_loss': stop_loss, 'target1': t1, 'target2': t2, 'rr1': rr1, 'rr2': rr2, 'rs_factor': rs,
        'pattern': pattern, 'news': news, 'market_regime': regime, 'oldwang': oldwang_metrics,
        'institutional': inst_breakdown, 'sparkline': sparkline_10d
    }, None

@st.cache_data(ttl=900, show_spinner=False)
def analyze_and_rank_pool(limit=30):
    candidates = get_top_investment_trust_stocks(limit=limit)
    rankings = []
    for symbol, meta in candidates.items():
        name = meta['name']
        trust_vol = meta.get('trust_buy_vol', 0)
        df = get_stock_history(symbol, period='3mo')
        if df.empty or len(df) < 15:
            continue
        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = round(float(last['Close']), 2)
        pct_change = round(((close - float(prev['Close'])) / float(prev['Close'])) * 100, 2)
        ma5 = round(float(last['5MA']), 2) if pd.notnull(last['5MA']) else close
        ma10 = round(float(last['10MA']), 2) if pd.notnull(last['10MA']) else close
        ma20 = round(float(last['20MA']), 2) if pd.notnull(last['20MA']) else close
        vol = float(last['Volume'])
        vol_ma20 = float(last['Vol_MA20']) if pd.notnull(last['Vol_MA20']) else vol
        score = 40
        signals, tags = [], []
        if trust_vol >= 1000:
            score += 25; signals.append(f"投信大舉重倉：買超 {trust_vol:,} 張"); tags.append("投信重倉")
        elif trust_vol >= 300:
            score += 15; signals.append(f"投信積極建倉：買超 {trust_vol:,} 張"); tags.append("投信進駐")
        if close > ma20:
            score += 15; signals.append("站穩 20MA 生命線（多方確立）")
        else:
            score -= 25; signals.append("跌破 20MA 生命線（偏弱整理）")
        if ma5 > ma10 and ma10 > ma20:
            score += 15; signals.append("均線多頭排列"); tags.append("多頭排列")
        if vol > vol_ma20 * 1.3:
            score += 15; signals.append("放量攻擊：成交量高於 20 日均量 30%"); tags.append("放量突破")
            
        stop_loss = round(min(ma20, float(df['Low'].iloc[-3:].min())), 2)
        target_price = round(close * 1.08, 2)
        rr_ratio = round(max(target_price - close, 0.1) / max(close - stop_loss, 0.1), 1)
        rankings.append({
            'symbol': symbol, 'name': name, 'close': close, 'pct_change': pct_change,
            'trust_vol': trust_vol, 'score': min(max(score, 0), 100), 'ma20': ma20,
            'stop_loss': stop_loss, 'target_price': target_price, 'rr_ratio': rr_ratio,
            'signals': signals, 'tags': tags
        })
    rankings.sort(key=lambda x: x['score'], reverse=True)
    return rankings

# ================= 5. 短線 5~20% 題材催化與法人連買狙擊模型 =================
@st.cache_data(ttl=900, show_spinner=False)
def get_short_term_catalyst_picks(limit=30):
    """
    短線 5~20% 獲利空間狙擊演算法：
    1. 法人連買/波段鎖碼
    2. 強勢題材關聯
    3. 量價動能突破或老王回測買黑
    4. 自動計算短線防守 (-3%~-4%)、T1目標 (+6%~+8%)、T2波段目標 (+15%~+22%)
    5. 產出操作燈號（🟢 建議買進 / 🟡 觀望蓄勢 / 🔴 偏空賣出）
    """
    streak_stocks = get_institutional_streak_stocks(limit=50)
    results = []
    
    # 候選池：1. 法人連買 2. 市場活躍股 3. 上櫃/興櫃生技重點股 4. 自選池
    candidates = {}
    for sym, meta in streak_stocks.items():
        candidates[sym] = meta
        
    # 納入全市場活躍熱門股
    active_hot = get_twse_market_active_stocks(limit=35)
    for h in active_hot:
        if h['symbol'] not in candidates:
            candidates[h['symbol']] = {
                'name': h['name'], 'streak_days': 1,
                'latest_buy_vol': int(h.get('trade_vol', 0) / 1000),
                'total_streak_vol': int(h.get('trade_vol', 0) / 1000),
                'streak_type': '⚡ 動能爆量焦點'
            }

    # 納入上櫃與興櫃重點生技族群 (泰合、仁新、藥華藥、保瑞、美時、順藥、合一、康霈等)
    biotech_focus = [
        ('6467', '泰合生技'), ('6696', '仁新'), ('6446', '藥華藥'), ('6472', '保瑞'),
        ('1795', '美時'), ('6535', '順藥'), ('4743', '合一'), ('6919', '康霈'),
        ('6785', '昱展新藥'), ('6617', '共信-KY'), ('4147', '中裕'), ('4174', '浩鼎'),
        ('4726', '永昕'), ('6875', '國邑*'), ('4771', '望隼'), ('6491', '晶碩')
    ]
    for b_sym, b_name in biotech_focus:
        if b_sym not in candidates:
            candidates[b_sym] = {
                'name': b_name, 'streak_days': 1,
                'latest_buy_vol': 500,
                'total_streak_vol': 500,
                'streak_type': '🧬 生技新藥強勢題材'
            }
            
    # 納入使用者自選追蹤池
    user_pool = load_custom_pool()
    for cp in user_pool:
        c_sym = cp['symbol']
        if c_sym not in candidates:
            candidates[c_sym] = {
                'name': cp.get('name', c_sym), 'streak_days': 1,
                'latest_buy_vol': 500,
                'total_streak_vol': 500,
                'streak_type': '⭐ 核心自選追蹤'
            }

    for sym, meta in candidates.items():
        df = get_stock_history(sym, period='3mo')
        if df.empty or len(df) < 5:
            continue
            
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else last
        close = round(float(last['Close']), 2)
        open_p = round(float(last['Open']), 2)
        prev_close = float(prev['Close'])
        pct_change = round(((close - prev_close) / (prev_close + 1e-9)) * 100, 2)
        
        ma5 = round(float(last['5MA']), 2) if ('5MA' in last and pd.notnull(last['5MA'])) else close
        ma10 = round(float(last['10MA']), 2) if ('10MA' in last and pd.notnull(last['10MA'])) else close
        ma20 = round(float(last['20MA']), 2) if ('20MA' in last and pd.notnull(last['20MA'])) else close
        vol = float(last['Volume'])
        vol_ma5 = float(last['Vol_MA5']) if ('Vol_MA5' in last and pd.notnull(last['Vol_MA5'])) else vol
        vol_ratio = round(vol / (vol_ma5 + 1e-9), 2)
        
        # 短線分數評估 (滿分 100)
        short_score = 50
        tags = []
        
        # 1. 均線發散多頭排列
        if close > ma5 and ma5 > ma10 and ma10 > ma20:
            short_score += 20
            tags.append("均線多頭發散")
        elif close > ma20:
            short_score += 10
            tags.append("站穩月線")
        else:
            short_score -= 25  # 破月線直接大幅扣分
            
        # 2. 籌碼或題材鎖碼力道
        streak_days = meta.get('streak_days', 1)
        streak_type = meta.get('streak_type', '法人買進')
        
        if '生技' in streak_type or '自選' in streak_type:
            short_score += 15
            tags.append(f"🔥 {streak_type}")
            
        if streak_days >= 3:
            short_score += 20
            tags.append(f"法人連買 {streak_days} 天")
        elif streak_days >= 2:
            short_score += 10
            tags.append(f"法人連買 2 天")
        elif meta.get('latest_buy_vol', 0) >= 1000:
            short_score += 15
            tags.append("單日千張大單")
            
        # 3. 妖股量能異動與短線爆發型態
        is_black_tested = (close < open_p) and (abs(close - ma5)/ma5 <= 0.02) and (vol < vol_ma5 * 1.1)
        is_breakout = (close >= float(df['High'].iloc[-10:-1].max())) if len(df) >= 10 else False
        is_monster_vol = (vol_ratio >= 2.0 and pct_change >= 4.0)  # 妖股爆量長紅異動
        
        if is_monster_vol:
            short_score += 25
            tags.append("⚡ 飆風妖股放量急攻")
            trigger_type = "妖股爆量起漲 (短線動能極強)"
        elif is_black_tested:
            short_score += 15
            tags.append("🎯 買黑回測守穩(高盈虧比)")
            trigger_type = "買黑不買紅 (回測守穩 5MA)"
        elif is_breakout and vol_ratio >= 1.5:
            short_score += 15
            tags.append("🚀 突破前高放量")
            trigger_type = "動能突破前高"
        else:
            trigger_type = "蓄勢整理"
            
        # 4. 判斷操作建議燈號
        if close < ma20 or short_score < 50:
            action_signal = "🔴 建議賣出 / 觀望"
        elif short_score >= 75 and (is_monster_vol or is_black_tested or is_breakout):
            action_signal = "🟢 強力買進"
        elif short_score >= 60 and close >= ma5:
            action_signal = "🟢 建議買進"
        else:
            action_signal = "🟡 觀望蓄勢"
            
        # 計算短線 5~20% 目標價與嚴格防守價
        stop_loss = round(max(close * 0.965, min(ma5 * 0.99, close * 0.95)), 2)
        target1 = round(close * 1.07, 2)   # T1: +7% 短線先跑一半
        target2 = round(close * 1.18, 2)   # T2: +18% 波段主升段
        
        risk_per_share = max(close - stop_loss, 0.1)
        reward_t1 = round((target1 - close) / risk_per_share, 1)
        reward_t2 = round((target2 - close) / risk_per_share, 1)
        
        results.append({
            'symbol': sym,
            'name': meta['name'],
            'close': close,
            'pct_change': pct_change,
            'short_score': min(max(short_score, 0), 100),
            'streak_days': streak_days,
            'streak_type': streak_type,
            'vol_ratio': vol_ratio,
            'trigger_type': trigger_type,
            'action_signal': action_signal,
            'stop_loss': stop_loss,
            'stop_loss_pct': round(((stop_loss - close)/close)*100, 1),
            'target1': target1,
            'target2': target2,
            'reward_t1': reward_t1,
            'reward_t2': reward_t2,
            'tags': tags,
            'sparkline': generate_sparkline(df['Close'].iloc[-10:])
        })
            
    results.sort(key=lambda x: x['short_score'], reverse=True)
    return results[:limit]