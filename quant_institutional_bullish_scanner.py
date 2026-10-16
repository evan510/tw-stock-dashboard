# -*- coding: utf-8 -*-
"""
=============================================================================
量化交易選股腳本：尋找「主力剛開始進場、技術面多頭排列」的強勢波段股
=============================================================================
篩選條件：
1. 籌碼面：三大法人（外資＋投信）近 3 個交易日連續同步買超 (外資買超>0 且 投信買超>0)。
2. 技術面：今日收盤價同時在 5日線、20日線（月線）、60日線（季線）之上，
          且三均線呈標準多頭排列 (Close > 5MA > 20MA > 60MA)。
3. 量能面：今日成交量大於 20日平均成交量的 1.5 倍 (主力放量表態進駐)。
4. 風險過濾：過濾掉近 20 日平均成交量小於 1000 張的殭屍股。
=============================================================================
"""

import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf

# 設定終端機標準輸出編碼
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def get_recent_trading_days(target_days=3):
    """取得台灣證券交易所最近具備法人資料的 N 個交易日"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    valid_dates = []
    for delta in range(12):
        d = datetime.now() - timedelta(days=delta)
        if d.weekday() < 5:  # 週一到週五
            d_str = d.strftime('%Y%m%d')
            url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?response=json&date={d_str}"
            try:
                res = requests.get(url, headers=headers, timeout=4).json()
                if res.get('stat') == 'OK' and res.get('data'):
                    valid_dates.append(d_str)
                    if len(valid_dates) >= target_days:
                        break
            except Exception:
                pass
    return valid_dates

def fetch_institutional_3d_synced_stocks(trading_days):
    """
    抓取近 3 個交易日外資 (TWT38U) 與投信 (TWT44U) 的買賣超日報，
    篩選出『連續 3 日外資與投信皆同步買超』的個股。
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    day_maps = []

    print(f"[*] 正在獲取最近 {len(trading_days)} 個營業日籌碼日報: {trading_days}")
    for d_str in trading_days:
        day_data = {}
        # 1. 投信買賣超 (TWT44U)
        try:
            r_trust = requests.get(f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?response=json&date={d_str}", headers=headers, timeout=5).json()
            for row in r_trust.get('data', []):
                sym = str(row[1]).strip()
                name = str(row[2]).strip()
                try:
                    net = int(str(row[5]).replace(',', '').strip())
                    if net > 0:
                        day_data.setdefault(sym, {'name': name})['trust'] = net
                except ValueError:
                    pass
        except Exception as e:
            print(f"[!] 讀取投信 {d_str} 異常: {e}")

        # 2. 外資買賣超 (TWT38U)
        try:
            r_foreign = requests.get(f"https://www.twse.com.tw/rwd/zh/fund/TWT38U?response=json&date={d_str}", headers=headers, timeout=5).json()
            for row in r_foreign.get('data', []):
                sym = str(row[1]).strip()
                name = str(row[2]).strip()
                try:
                    net = int(str(row[5]).replace(',', '').strip())
                    if net > 0:
                        day_data.setdefault(sym, {'name': name})['foreign'] = net
                except ValueError:
                    pass
        except Exception as e:
            print(f"[!] 讀取外資 {d_str} 異常: {e}")

        day_maps.append(day_data)

    # 判定 3 天同時連續買超
    synced = {}
    if len(day_maps) >= 3:
        for sym, meta in day_maps[0].items():
            if len(sym) != 4 or not sym.isdigit():
                continue  # 過濾 ETF、權證
            if meta.get('trust', 0) > 0 and meta.get('foreign', 0) > 0:
                d2 = day_maps[1].get(sym, {})
                d3 = day_maps[2].get(sym, {})
                if d2.get('trust', 0) > 0 and d2.get('foreign', 0) > 0 and d3.get('trust', 0) > 0 and d3.get('foreign', 0) > 0:
                    trust_total = meta.get('trust', 0) + d2.get('trust', 0) + d3.get('trust', 0)
                    foreign_total = meta.get('foreign', 0) + d2.get('foreign', 0) + d3.get('foreign', 0)
                    synced[sym] = {
                        'name': meta.get('name', ''),
                        'trust_3d_lots': trust_total // 1000,
                        'foreign_3d_lots': foreign_total // 1000,
                        'total_3d_lots': (trust_total + foreign_total) // 1000
                    }
    return synced

def scan_bullish_breakout():
    print("=" * 75)
    print("🚀 台股量化選股：主力剛進場＋多頭排列強勢波段股篩選中...")
    print("=" * 75)

    # 步驟 1: 取得交易日
    days = get_recent_trading_days(target_days=3)
    if len(days) < 3:
        print("[!] 查無足夠交易日籌碼數據。")
        return []

    # 步驟 2: 篩選籌碼面 (近 3 日外資+投信連續同步買超)
    candidates = fetch_institutional_3d_synced_stocks(days)
    print(f"[+] 符合【近3日外資＋投信連續同步買超】候選股共: {len(candidates)} 檔")
    if not candidates:
        print("[-] 今日無符合籌碼條件標的。")
        return []

    # 步驟 3: 批次透過 yfinance 檢驗技術面、量能面與流動性
    tickers = [f"{s}.TW" for s in candidates.keys()]
    print(f"[*] 正在拉取 {len(tickers)} 檔候選股日 K 線量價歷史數據...")
    try:
        data = yf.download(tickers, period='4mo', progress=False)
    except Exception as e:
        print(f"[!] yfinance 下載失敗: {e}")
        return []

    matched_stocks = []
    for sym, meta in candidates.items():
        ticker = f"{sym}.TW"
        try:
            if len(tickers) == 1:
                df = pd.DataFrame({'Close': data['Close'], 'Volume': data['Volume']}).dropna()
            else:
                if ticker not in data['Close']:
                    continue
                df = pd.DataFrame({'Close': data['Close'][ticker], 'Volume': data['Volume'][ticker]}).dropna()

            if len(df) < 60:
                continue

            close = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            pct_change = round(((close - prev_close) / prev_close) * 100, 2)

            # 均線計算 (5MA, 20MA, 60MA)
            ma5 = float(df['Close'].rolling(5).mean().iloc[-1])
            ma20 = float(df['Close'].rolling(20).mean().iloc[-1])
            ma60 = float(df['Close'].rolling(60).mean().iloc[-1])

            # 成交量計算 (今日量, 20MA量)
            vol_today = float(df['Volume'].iloc[-1])
            vol_ma20 = float(df['Volume'].rolling(20).mean().iloc[-1])

            # 條件 2: 技術面 Close > 5MA > 20MA > 60MA
            is_bullish_ma = (close > ma5) and (ma5 > ma20) and (ma20 > ma60)
            if not is_bullish_ma:
                continue

            # 條件 3: 量能面 今日量 >= 20MA量 * 1.5 倍
            is_vol_surge = (vol_today >= vol_ma20 * 1.5)
            if not is_vol_surge:
                continue

            # 條件 4: 流動性過濾 20MA均量 >= 1000 張 (1,000,000 股)
            is_liquid = (vol_ma20 >= 1000 * 1000)
            if not is_liquid:
                continue

            vol_ratio = round(vol_today / (vol_ma20 + 1e-9), 2)
            vol_ma20_k = round(vol_ma20 / 1000, 0)

            # 波段目標與防守停損價 (老王均線戰法)
            stop_loss = round(max(ma20 * 0.985, close * 0.95), 2)
            target1 = round(close * 1.07, 2)   # 短線目標 +7%
            target2 = round(close * 1.18, 2)   # 波段目標 +18%

            matched_stocks.append({
                '代號': sym,
                '名稱': meta['name'],
                '現價': close,
                '今日漲跌幅': f"{pct_change:+,.2f}%",
                '5MA': round(ma5, 2),
                '20MA(月線)': round(ma20, 2),
                '60MA(季線)': round(ma60, 2),
                '今日量能倍數': f"{vol_ratio} 倍",
                '20日均量(張)': int(vol_ma20_k),
                '投信3日買超(張)': meta['trust_3d_lots'],
                '外資3日買超(張)': meta['foreign_3d_lots'],
                '防守停損價': stop_loss,
                'T1短線目標(+7%)': target1,
                'T2波段目標(+18%)': target2,
                '_sort_key': vol_ratio
            })
        except Exception:
            continue

    # 排序：依量能倍數降序
    matched_stocks.sort(key=lambda x: x['_sort_key'], reverse=True)
    for row in matched_stocks:
        row.pop('_sort_key', None)

    return matched_stocks

if __name__ == '__main__':
    results = scan_bullish_breakout()
    if results:
        df_out = pd.DataFrame(results)
        print("\n" + "=" * 75)
        print("🎯【量化選股成功】符合「主力3日連買＋均線多頭＋爆量1.5x＋均量>1000張」標的：")
        print("=" * 75)
        print(df_out.to_string(index=False))
        print("=" * 75)
    else:
        print("\n[-] 全市場今日暫無同時滿足 4 項嚴苛條件之標的，建議多看少做、保留現金。")
