# -*- coding: utf-8 -*-
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd

from data_engine import (
    get_macro_overview,
    get_institutional_investors_summary,
    get_stock_history,
    get_stock_news,
    resolve_stock
)
from strategy_engine import (
    calculate_market_regime,
    evaluate_oldwang_strategy,
    analyze_dynamic_market_hot_stocks,
    analyze_custom_pool_stocks,
    analyze_curated_theme_stocks,
    run_ai_deep_analysis,
    analyze_and_rank_pool
)
from custom_pool_manager import load_custom_pool, add_to_custom_pool, remove_from_custom_pool
from portfolio_manager import load_portfolio, add_holding, remove_holding, evaluate_holdings
from notifier import load_alert_settings, save_alert_settings, send_line_notify, send_webhook_alert
import config

st.set_page_config(
    page_title=f"{config.APP_TITLE} {config.APP_VERSION}",
    page_icon=config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# 判斷台股盤中/盤後時段
now = datetime.now()
is_tw_trading = (now.weekday() < 5) and (
    (now.hour == 9) or (now.hour > 9 and now.hour < 13) or (now.hour == 13 and now.minute <= 35)
)
market_time_tag = "🔴 盤中交易 (延遲15分)" if is_tw_trading else "🟢 盤後結算 (日K統計完備)"

# ----------------- 頂級 RWD 深色專業操盤 CSS -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0f131a;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label {
        padding: 10px 14px !important;
        margin-bottom: 6px !important;
        border-radius: 8px !important;
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid transparent !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:hover {
        background: rgba(59, 130, 246, 0.08) !important;
        border-color: rgba(59, 130, 246, 0.25) !important;
        transform: translateX(3px);
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"],
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(90deg, rgba(59, 130, 246, 0.16) 0%, rgba(59, 130, 246, 0.04) 100%) !important;
        border: 1px solid rgba(59, 130, 246, 0.4) !important;
        border-left: 4px solid #3b82f6 !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label p {
        font-size: 0.92rem !important;
        font-weight: 500 !important;
        color: #e2e8f0 !important;
        letter-spacing: 0.3px;
        margin: 0 !important;
    }
    
    .rwd-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .rwd-card:hover {
        border-color: rgba(96, 165, 250, 0.3);
        transform: translateY(-2px);
    }
    
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        .rwd-card {
            padding: 14px 14px !important;
            margin-bottom: 12px !important;
        }
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.25rem !important; }
        h3 { font-size: 1.1rem !important; }
        .stMetric { padding: 8px 10px !important; }
    }
    
    .pill {
        display: inline-flex;
        align-items: center;
        padding: 3px 9px;
        border-radius: 8px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 4px;
    }
    .pill-blue { background: rgba(59, 130, 246, 0.18); color: #60a5fa; border: 1px solid rgba(96, 165, 250, 0.3); }
    .pill-buy { background: rgba(34, 197, 94, 0.18); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.3); }
    .pill-hot { background: rgba(239, 68, 68, 0.18); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.3); }
    .pill-warn { background: rgba(245, 158, 11, 0.18); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.3); }
    .pill-purple { background: rgba(168, 85, 247, 0.18); color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.3); }
    
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- 側邊欄導航 (新增第3頁老王戰法) -----------------
st.sidebar.markdown(
    f"""
    <div style="padding: 4px 0 10px 0;">
        <h2 style="margin:0; font-size:1.35rem; font-weight:800; color:#ffffff; letter-spacing:0.5px;">
            {config.APP_ICON} {config.APP_TITLE}
        </h2>
        <div style="margin-top:6px;">
            <span class="pill pill-blue">RELEASE {config.APP_VERSION}</span>
        </div>
    </div>
    """, 
    unsafe_allow_html=True
)

menu = st.sidebar.radio(
    "功能導航：",
    [
        "🔥 1. 熱門焦點與短線突破 (含大盤評分與RS)",
        "🧠 2. AI 個股量化與部位試算 (雙階停利+1%風控)",
        "👑 3. 老王均線獨門戰法 (萬里無雲/買黑不買紅)",
        "🎯 4. 投信鎖碼波段選股榜",
        "🌐 5. 盤後宏觀與法人籌碼",
        "📈 6. 互動 K 線與指標圖室",
        "💼 7. 庫存管家與防守警報 (含Line通知)",
        "📖 8. 短線與波段操盤心法"
    ],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.caption(f"時段狀態：{market_time_tag}")
if st.sidebar.button("🔄 同步刷新數據", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(f"系統時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
st.sidebar.caption("✅ 支援手機 RWD 直式介面操作")

# ================= 頁面 1：熱門焦點與短線突破 (含大盤評分與RS) =================
if menu == "🔥 1. 熱門焦點與短線突破 (含大盤評分與RS)":
    st.title("🔥 市場熱門焦點股與短線突破量化評估")
    
    m_regime = calculate_market_regime()
    st.markdown(f"""
    <div class="rwd-card" style="border-left: 5px solid {'#22c55e' if m_regime['score'] >= 75 else ('#f59e0b' if m_regime['score'] >= 40 else '#ef4444')};">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
            <div>
                <span style="font-size:0.85rem; color:#94a3b8; font-weight:600;">MARKET REGIME 大盤短線環境評分</span>
                <h3 style="margin:2px 0 0 0;">{m_regime['status']} ｜ 體質分數：<span style="color:#60a5fa; font-weight:700;">{m_regime['score']} / 100</span></h3>
            </div>
            <div style="text-align:right;">
                <span class="pill {'pill-buy' if m_regime['score'] >= 40 else 'pill-hot'}">
                    {'🔓 允許執行 BUY 突破訊號' if m_regime['score'] >= 40 else '🔒 啟動風控：全域禁止 BUY'}
                </span>
            </div>
        </div>
        <p style="margin:6px 0 0 0; font-size:0.85rem; color:#cbd5e1;">👉 {m_regime['desc']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs([
        "⚡ 分頁 A：全市場動態成交熱門榜 (含 RS & 型態)",
        "🛠️ 分頁 B：我的自選題材追蹤池",
        "💎 分頁 C：精選產業主流題材庫"
    ])
    
    with tab1:
        st.subheader("⚡ 全市場即時成交爆量熱門股 Top 30")
        with st.spinner("自動掃描全市場成交額榜單並運算量價結構中..."):
            market_hot = analyze_dynamic_market_hot_stocks(limit=30)
            
        if market_hot:
            can_buy_c = sum(1 for x in market_hot if "BUY" in x['entry_signal'])
            overheat_c = sum(1 for x in market_hot if "過度延伸" in x['entry_signal'])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("今日熱門掃描", f"{len(market_hot)} 檔")
            c2.metric("🟢 浮現突破/蓄勢買點", f"{can_buy_c} 檔")
            c3.metric("⚠️ 過度延伸嚴禁追高", f"{overheat_c} 檔")
            
            st.markdown("#### 🔥 前 6 大成交核心焦點卡片")
            cards = market_hot[:6]
            for i in range(0, len(cards), 3):
                cols = st.columns([1, 1, 1])
                for j in range(3):
                    if i + j < len(cards):
                        it = cards[i + j]
                        with cols[j]:
                            pill_class = "pill-buy" if "BUY" in it['entry_signal'] else ("pill-hot" if "過度" in it['entry_signal'] else "pill-warn")
                            rs_pill = "pill-purple" if it['rs_factor'] > 0 else "pill-warn"
                            st.markdown(f"""
                            <div class="rwd-card">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <h3 style="margin:0;">{it['name']} <span style="font-size:0.9rem; color:gray;">({it['symbol']})</span></h3>
                                    <div>
                                        <span class="pill {rs_pill}">RS: {it['rs_factor']:+}%</span>
                                        <span class="pill {pill_class}">{it['pattern']}</span>
                                    </div>
                                </div>
                                <h2 style="margin:8px 0; color:#ef4444;">${it['close']} <span style="font-size:1rem; color:#ef4444;">+{it['pct_change']}%</span></h2>
                                <p style="margin:4px 0; font-size:0.85rem; color:#cbd5e1;">💰 成交金額：<b>約 {it['turnover_billion']} 億元</b></p>
                                <p style="margin:4px 0; font-size:0.85rem; color:#cbd5e1;">📊 今日量能：<b>均量 {it['vol_ratio']} 倍</b> ｜ RSI: <b>{it['rsi']}</b></p>
                                <div style="background:rgba(255,255,255,0.03); border-radius:8px; padding:8px; margin-top:8px;">
                                    <span style="font-size:0.82rem; color:#93c5fd;">👉 {it['action_advice']}</span>
                                </div>
                                <p style="margin:8px 0 0 0; font-size:0.82rem; color:#94a3b8;">🛡️ 防守停損：<b>${it['stop_loss']}</b> ｜ 🎯 第一目標：<b>${it['target1']}</b></p>
                            </div>
                            """, unsafe_allow_html=True)
                            
            st.markdown("#### 📋 全市場 Top 30 短線量能詳細清單")
            df_m = pd.DataFrame([
                {
                    '代號': x['symbol'], '名稱': x['name'], '成交金額(億)': x['turnover_billion'],
                    '現價': x['close'], '漲跌幅': f"{x['pct_change']}%", '量能倍數': f"{x['vol_ratio']}x",
                    'RS相對強度': f"{x['rs_factor']:+}%", '短線型態': x['pattern'],
                    '進場決策': x['entry_signal'], '防守停損價': x['stop_loss'], '目標價1': x['target1']
                } for x in market_hot
            ])
            st.dataframe(df_m, use_container_width=True)
            
    with tab2:
        st.subheader("🛠️ 我的自選題材追蹤池")
        with st.expander("➕ 新增股票 / ETF 至自選追蹤池", expanded=False):
            f1, f2, f3, f4 = st.columns(4)
            in_sym = f1.text_input("股票/ETF 代號或名稱 (如 00878, 6467, 泰合)", key="custom_sym")
            in_name = f2.text_input("名稱 (選填，留空自動查詢)", key="custom_name")
            in_tag = f3.text_input("族群標籤 (選填，如 高股息, 生技)", key="custom_tag")
            in_note = f4.text_input("自訂備註 (選填)", key="custom_note")
            if st.button("確認加入自選池", use_container_width=True):
                if in_sym:
                    with st.spinner("正在自動解析股票/ETF..."):
                        res_sym, auto_name = resolve_stock(in_sym)
                        final_name = in_name.strip() if in_name and in_name.strip() else auto_name
                        ok, msg = add_to_custom_pool(res_sym, final_name, in_tag, in_note)
                    st.success(f"已成功加入：{final_name} ({res_sym})！")
                    st.rerun()
                    
        custom_pool = load_custom_pool()
        if custom_pool:
            custom_analysis = analyze_custom_pool_stocks(custom_pool)
            for item in custom_analysis:
                with st.container():
                    c_head, c_del = st.columns([5, 1])
                    with c_head:
                        st.markdown(f"### {item['name']} ({item['symbol']}) <span class='pill pill-blue'>{item['tag']}</span> <span class='pill pill-purple'>RS: {item['rs_factor']:+}%</span> `{item['entry_signal']}`", unsafe_allow_html=True)
                    with c_del:
                        if st.button("🗑️ 移出", key=f"del_c_{item['symbol']}"):
                            remove_from_custom_pool(item['symbol'])
                            st.rerun()
                    inf1, inf2, inf3, inf4 = st.columns(4)
                    inf1.metric("現價", f"${item['close']}", f"{item['pct_change']}%")
                    inf2.write(f"• 今日量能：**均量 {item['vol_ratio']} 倍**")
                    inf3.write(f"• 短線型態：**{item['pattern']}**")
                    inf4.markdown(f"🛡️ **防守停損**：`${item['stop_loss']}` ｜ 🎯 **目標**：`${item['target1']}`")
                    st.info(f"👉 **操盤建議**：{item['action_advice']}")
                    st.markdown("---")
        else:
            st.info("目前自選池為空，點擊上方展開表單新增！")

    with tab3:
        st.subheader("💎 市場核心題材庫 (生技拆股、ETF、AI、CPO、設備、重電)")
        with st.spinner("計算精選產業題材量價動能中..."):
            curated_list = analyze_curated_theme_stocks()
        df_c = pd.DataFrame([
            {
                '代號': x['symbol'], '名稱': x['name'], '族群題材': x['theme'],
                '現價': x['close'], '漲跌幅': f"{x['pct_change']}%", 'RS強度': f"{x['rs_factor']:+}%",
                '短線型態': x['pattern'], '進場決策': x['entry_signal'], '防守停損價': x['stop_loss']
            } for x in curated_list
        ])
        st.dataframe(df_c, use_container_width=True)

# ================= 頁面 2：AI 個股量化與部位試算 (雙階停利+1%風控) =================
elif menu == "🧠 2. AI 個股量化與部位試算 (雙階停利+1%風控)":
    st.title("🧠 個股 / ETF AI 深度量化診斷室")
    st.caption("支援輸入上市櫃代號 (如 6467, 2330)、ETF (如 00878, 0050) 或中文名稱 (如 泰合, 仁新)")
    
    col_in1, col_in2 = st.columns([3, 1])
    with col_in1:
        query_input = st.text_input("請輸入台股/ETF 代號或名稱：", value="00878").strip()
    with col_in2:
        st.write("")
        st.write("")
        st.button("🚀 啟動 AI 深度分析", type="primary", use_container_width=True)
        
    if query_input:
        with st.spinner(f"AI 操盤引擎正在全面掃描『{query_input}』之技術面與籌碼..."):
            data, err = run_ai_deep_analysis(query_input)
            
        if err:
            st.error(err)
        else:
            st.markdown(f"""
            <div class="rwd-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h2 style="margin:0;">{data['name']} <span style="font-size:1.2rem; color:gray;">({data['symbol']})</span></h2>
                        <span class="pill pill-blue">AI 短線量化診斷報告</span>
                        <span class="pill pill-purple">RS 相對大盤：{data['rs_factor']:+}%</span>
                    </div>
                    <div style="text-align:right;">
                        <h1 style="margin:0; color:#ef4444;">${data['close']}</h1>
                        <span style="color:#ef4444; font-weight:600;">+{data['pct_change']}%</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"### 🎯 短線操盤行動決策：**{data['ai_verdict']}** ｜ 型態：`{data['pattern']}`")
            p1, p2, p3, p4 = st.columns(4)
            p1.success(f"📥 **建議進場區間**\n\n**{data['entry_zone']}**")
            p2.error(f"🛑 **波段防守停損價**\n\n**`${data['stop_loss']}`**")
            p3.info(f"🎯 **雙階獲利目標**\n\nT1: **`${data['target1']}`** (平倉50%)\nT2: **`${data['target2']}`** (讓利潤奔跑)")
            p4.warning(f"⚖️ **風險報酬比 (R/R)**\n\nRR1: **{data['rr1']} : 1**\nRR2: **{data['rr2']} : 1**")
            
            st.markdown("---")
            st.markdown("#### 🧮 1% 帳戶風險部位試算機 (Position Sizer)")
            st.caption("依據短線交易紀律：單筆虧損絕對不超過總本金的 1%，由停損距離嚴格反推可買股數！")
            
            col_calc1, col_calc2 = st.columns(2)
            with col_calc1:
                account_capital = st.number_input("您的總本金帳戶金額 (元)：", min_value=10000.0, value=1000000.0, step=50000.0)
            with col_calc2:
                risk_pct = st.number_input("單筆最大承受風險比例 (%)：", min_value=0.5, max_value=3.0, value=1.0, step=0.1)
                
            max_risk_dollar = account_capital * (risk_pct / 100.0)
            risk_per_share = max(data['close'] - data['stop_loss'], 0.1)
            
            if data['close'] > data['stop_loss'] and "過度延伸" not in data['ai_verdict']:
                allowed_shares = int(max_risk_dollar // risk_per_share)
                required_capital = round(allowed_shares * data['close'], 0)
                capital_ratio = round((required_capital / account_capital) * 100, 1)
                
                c_s1, c_s2, c_s3, c_s4 = st.columns(4)
                c_s1.metric("💡 建議建倉股數", f"{allowed_shares:,} 股", f"約 {round(allowed_shares/1000, 1)} 張")
                c_s2.metric("🛑 若被停損最大虧損", f"-${max_risk_dollar:,.0f} 元", f"嚴格鎖定在 {risk_pct}%")
                c_s3.metric("💰 需動用資金", f"${required_capital:,.0f} 元")
                c_s4.metric("📊 佔總本金比率", f"{capital_ratio}%")
                
                if capital_ratio > 40.0:
                    st.warning("⚠️ 提示：該筆交易動用超過 40% 總資金，請留意單一標的過度集中風險！")
            else:
                st.error("⚠️ 當前現價已逼近停損點或處於過度延伸區，風險報酬不對稱，系統建議建倉 0 股！")
                
            st.markdown("---")
            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown("#### 🔍 主力買盤力道與量能")
                st.write(f"• **當前買盤力道**：{data['buying_power']}")
                st.write(f"• **量價結構診斷**：{data['vol_structure']}")
                st.write(f"• **量能放大倍數**：20日均量之 **{data['vol_ratio']} 倍**")
            with c_right:
                st.markdown("#### 📈 均線位階與多空架構")
                st.write(f"• 5MA：**${data['ma5']}** ｜ 10MA：**${data['ma10']}**")
                st.write(f"• 20MA (生命線)：**${data['ma20']}** ｜ 60MA：**${data['ma60']}**")
                if data['close'] > data['ma20']:
                    st.success("✔ 股價站穩 20MA 生命線之上，多方結構完整。")
                else:
                    st.error("✖ 股價跌破 20MA 月線生命線，短中期偏空整理。")
                    
            st.markdown("---")
            st.markdown(f"#### 📰 【{data['name']}】最新重大財經新聞")
            if data['news']:
                for n in data['news']:
                    st.markdown(f"• [{n['title']}]({n['link']}) — <small style='color:gray'>{n['date']}</small>", unsafe_allow_html=True)

# ================= 頁面 3：老王均線獨門戰法 (萬里無雲/買黑不買紅) =================
elif menu == "👑 3. 老王均線獨門戰法 (萬里無雲/買黑不買紅)":
    st.title("👑 老王均線獨門戰法特輯")
    st.caption("源自《oldwangstock 老王愛說笑》操盤金律：均線為最高天條、萬里無雲、買黑不買紅、破線無條件停損！")
    
    ow_tab1, ow_tab2, ow_tab3 = st.tabs([
        "🚀 模組 A：萬里無雲 (三陽開泰) 飆股池",
        "🎯 模組 B：老王絕活「買黑不買紅」精選",
        "🔍 模組 C：個股老王均線與大量K體檢機"
    ])
    
    with ow_tab1:
        st.subheader("🚀 萬里無雲 (三陽開泰) — 均線多頭排列且上檔無壓力")
        st.caption("老王定義：收盤同時站上 5MA、10MA、20MA 三線，且 5MA > 10MA > 20MA 多頭發散！")
        with st.spinner("掃描市場萬里無雲標的中..."):
            m_hot = analyze_dynamic_market_hot_stocks(limit=30)
            wanli_stocks = []
            for s in m_hot:
                ow = evaluate_oldwang_strategy(s['symbol'])
                if ow and ow['is_wan_li']:
                    wanli_stocks.append({
                        '代號': s['symbol'], '名稱': s['name'], '現價': ow['close'],
                        '漲跌幅': f"{ow['pct_change']}%", '5MA': ow['ma5'], '10MA': ow['ma10'],
                        '20MA(生命線)': ow['ma20'], '老王評語': ow['cloud_status']
                    })
        if wanli_stocks:
            st.dataframe(pd.DataFrame(wanli_stocks), use_container_width=True)
        else:
            st.info("目前熱門榜暫無完全符合萬里無雲標的，市場處於均線震盪！")
            
    with ow_tab2:
        st.subheader("🎯 老王招牌「買黑不買紅」— 回測 5MA/10MA 守穩量縮切入點")
        st.caption("老王名言：散戶最愛追大紅棒，老手只在『突破後拉回收黑K、回測均線不破且量縮』時買進！")
        with st.spinner("過濾買黑不買紅高盈虧比標的中..."):
            m_hot = analyze_dynamic_market_hot_stocks(limit=30)
            buy_black_stocks = []
            for s in m_hot:
                ow = evaluate_oldwang_strategy(s['symbol'])
                if ow and ow['is_buy_black']:
                    buy_black_stocks.append({
                        '代號': s['symbol'], '名稱': s['name'], '現價': ow['close'],
                        '今日K棒': '黑K (拉回)', '5MA支撐': ow['ma5'], '10MA支撐': ow['ma10'],
                        '防守大量K低點': ow['max_vol_low'], '老王建議': '🟢 買點浮現：量縮回測有守'
                    })
        if buy_black_stocks:
            st.dataframe(pd.DataFrame(buy_black_stocks), use_container_width=True)
        else:
            st.info("今日無恰好回測 5MA/10MA 守穩之量縮黑K標的。")

    with ow_tab3:
        st.subheader("🔍 個股老王均線與大量K防守體檢機")
        col_ow1, col_ow2 = st.columns([3, 1])
        with col_ow1:
            ow_input = st.text_input("輸入股票或 ETF 代號/名稱：", value="6467", key="ow_search").strip()
        with col_ow2:
            st.write("")
            st.write("")
            st.button("執行老王體檢", use_container_width=True)
            
        if ow_input:
            r_s, r_n = resolve_stock(ow_input)
            ow_res = evaluate_oldwang_strategy(r_s)
            if ow_res:
                st.markdown(f"""
                <div class="rwd-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <h3 style="margin:0;">{r_n} ({r_s}) — {ow_res['cloud_status']}</h3>
                            <span style="font-size:0.85rem; color:#94a3b8;">{ow_res['cloud_desc']}</span>
                        </div>
                        <h2 style="margin:0; color:#ef4444;">${ow_res['close']}</h2>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                ow_c1, ow_c2, ow_c3, ow_c4 = st.columns(4)
                ow_c1.metric("5MA 短線減碼點", f"${ow_res['ma5']}", "跌破先賣一半")
                ow_c2.metric("10MA / 20MA 生命線", f"${ow_res['ma20']}", "破線全數清倉")
                ow_c3.metric("近20日大量K低點", f"${ow_res['max_vol_low']}", f"於 {ow_res['max_vol_date']} 爆量")
                ow_c4.metric("季線 (60MA)", f"${ow_res['ma60']}", "波段大防守")
                
                st.markdown("#### 🚨 老王即時出場警報診斷")
                if "🛑" in ow_res['exit_alert'] or "💣" in ow_res['exit_alert']:
                    st.error(ow_res['exit_alert'])
                elif "⚠️" in ow_res['exit_alert']:
                    st.warning(ow_res['exit_alert'])
                else:
                    st.success(ow_res['exit_alert'])

# ================= 頁面 4：投信鎖碼波段選股榜 =================
elif menu == "🎯 4. 投信鎖碼波段選股榜":
    st.title("🎯 投信鎖碼波段選股榜")
    st.caption("連線證交所全市場投信真實買超前 30 名，多因子挑出 Top 5")
    
    @st.cache_data(ttl=1200)
    def cached_rankings():
        return analyze_and_rank_pool(limit=30)
    with st.spinner("抓取投信買賣超排行榜中..."):
        all_ranks = cached_rankings()
    top5 = all_ranks[:5]
    if top5:
        st.subheader("🔥 投信波段鎖碼精選 Top 5 (持股 1~2 週)")
        cols = st.columns(len(top5))
        for i, s in enumerate(top5):
            with cols[i]:
                st.markdown(f"""
                <div class="rwd-card">
                    <h3 style="margin:0;">{s['name']}</h3>
                    <p style="color:gray; font-size:0.8rem; margin:0;">({s['symbol']})</p>
                    <h2 style="margin:6px 0; color:#ef4444;">${s['close']} <span style="font-size:0.9rem;">+{s['pct_change']}%</span></h2>
                    <p style="font-size:0.85rem; margin:2px 0;">評分：<b>{s['score']} / 100</b></p>
                    <p style="font-size:0.85rem; margin:2px 0;">🛡️ 防守價：<b>${s['stop_loss']}</b></p>
                    <p style="font-size:0.85rem; margin:2px 0;">🎯 目標價：<b>${s['target_price']}</b></p>
                </div>
                """, unsafe_allow_html=True)
                with st.expander("入選理由"):
                    for sig in s['signals']:
                        st.write(f"• {sig}")
        st.markdown("---")
        st.subheader("📋 投信買超鎖碼評分總榜單 (Top 30)")
        df_display = pd.DataFrame([
            {
                '代號': item['symbol'], '名稱': item['name'], '收盤價': item['close'],
                '漲跌幅(%)': f"{item['pct_change']}%", '投信買超(張)': f"{item['trust_vol']:,}",
                '量化分數': item['score'], '20MA月線': item['ma20'], '建議防守價': item['stop_loss']
            } for item in all_ranks
        ])
        st.dataframe(df_display, use_container_width=True)

# ================= 頁面 5：盤後宏觀與法人籌碼 =================
elif menu == "🌐 5. 盤後宏觀與法人籌碼":
    st.title("🌐 盤後宏觀總覽與三大法人資金風向標")
    macro = get_macro_overview()
    funds = get_institutional_investors_summary()
    st.subheader("📊 國際連動與核心指數")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("加權指數", f"{macro.get('加權指數',{}).get('close',0)}", f"{macro.get('加權指數',{}).get('pct',0)}%")
    with col2:
        st.metric("櫃買指數", f"{macro.get('櫃買指數',{}).get('close',0)}", f"{macro.get('櫃買指數',{}).get('pct',0)}%")
    with col3:
        st.metric("台積電 ADR", f"${macro.get('台積電ADR',{}).get('close',0)}", f"{macro.get('台積電ADR',{}).get('pct',0)}%")
    with col4:
        st.metric("輝達 NVDA", f"${macro.get('輝達 (NVDA)',{}).get('close',0)}", f"{macro.get('輝達 (NVDA)',{}).get('pct',0)}%")
    with col5:
        st.metric("費城半導體", f"{macro.get('費城半導體',{}).get('close',0)}", f"{macro.get('費城半導體',{}).get('pct',0)}%")
    st.markdown("---")
    st.subheader("💰 三大法人當日買賣超 (億元)")
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("外資買賣超", f"{funds['外資']} 億", delta=f"{funds['外資']}")
    f2.metric("投信買賣超", f"{funds['投信']} 億", delta=f"{funds['投信']}")
    f3.metric("自營商買賣超", f"{funds['自營商']} 億", delta=f"{funds['自營商']}")
    f4.metric("三大法人總計", f"{funds['合計']} 億", delta=f"{funds['合計']}")

# ================= 頁面 6：互動 K 線與指標圖室 =================
elif menu == "📈 6. 互動 K 線與指標圖室":
    st.title("📈 專業互動 K 線圖室 (台股 紅漲 🔴 / 綠跌 🟢)")
    st.caption("支援輸入代號（如 00878, 0050, 6467）或中文名稱（如 泰合, 仁新）")
    col_k1, col_k2 = st.columns([3, 1])
    with col_k1:
        sym_in = st.text_input("輸入股票/ETF 代號或名稱：", value="00878").strip()
    with col_k2:
        st.write("")
        st.write("")
        st.button("更新線圖", use_container_width=True)
    if sym_in:
        real_sym, real_name = resolve_stock(sym_in)
        df = get_stock_history(real_sym, period='4mo')
        if not df.empty:
            st.markdown(f"##### 📈 【{real_name} ({real_sym})】日 K 線與均線布林系統")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing_line_color='#ef4444', decreasing_line_color='#22c55e',
                name='K線'
            ))
            fig.add_trace(go.Scatter(x=df.index, y=df['5MA'], line=dict(color='#f59e0b', width=1.5), name='5MA'))
            fig.add_trace(go.Scatter(x=df.index, y=df['10MA'], line=dict(color='#a855f7', width=1.5), name='10MA'))
            fig.add_trace(go.Scatter(x=df.index, y=df['20MA'], line=dict(color='#3b82f6', width=2.2), name='20MA(生命線)'))
            fig.add_trace(go.Scatter(x=df.index, y=df['60MA'], line=dict(color='#10b981', width=1.5), name='60MA(季線)'))
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], line=dict(color='gray', width=1, dash='dash'), name='布林上軌'))
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], line=dict(color='gray', width=1, dash='dash'), name='布林下軌'))
            fig.update_layout(
                xaxis_rangeslider_visible=False, height=500,
                margin=dict(l=10, r=10, t=30, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"查無 {real_name} ({real_sym}) 之歷史量價數據。")

# ================= 頁面 7：庫存管家與防守警報 (含Line通知) =================
elif menu == "💼 7. 庫存管家與防守警報 (含Line通知)":
    st.title("💼 我的持股庫存管家與即時風險警報")
    
    # 警報通知推播設定區塊
    with st.expander("🔔 Line Notify / Webhook 警報通知設定", expanded=False):
        alert_cfg = load_alert_settings()
        n_c1, n_c2 = st.columns(2)
        line_token = n_c1.text_input("Line Notify 權杖 (Token)：", value=alert_cfg.get("line_token", ""), type="password", help="前往 https://notify-bot.line.me/ 申請權杖並加入群組")
        webhook_url = n_c2.text_input("Webhook URL (Discord/Slack/Telegram)：", value=alert_cfg.get("webhook_url", ""), type="password")
        
        btn_save_alert, btn_test_line = st.columns(2)
        if btn_save_alert.button("💾 儲存通知設定", use_container_width=True):
            alert_cfg["line_token"] = line_token.strip()
            alert_cfg["webhook_url"] = webhook_url.strip()
            save_alert_settings(alert_cfg)
            st.success("通知設定已儲存！")
        if btn_test_line.button("📲 發送測試訊息到 Line", use_container_width=True):
            ok, msg = send_line_notify("【台股戰情室 v4.3】Line Notify 測試訊息：系統連線正常！", token=line_token.strip())
            if ok:
                st.success(msg)
            else:
                st.error(msg)
                
    st.markdown("---")
    with st.expander("➕ 新增持股 / ETF 記錄", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        n_sym = c1.text_input("代號或名稱 (如 00878, 6467, 泰合)")
        n_name = c2.text_input("名稱 (選填，留空自動查詢)")
        n_cost = c3.number_input("買進成本價格", min_value=1.0, value=20.0, step=0.5)
        n_shares = c4.number_input("股數 (1張=1000股)", min_value=1, value=1000, step=100)
        if st.button("確認加入庫存部位", use_container_width=True):
            if n_sym:
                r_s, r_n = resolve_stock(n_sym)
                final_name = n_name.strip() if n_name and n_name.strip() else r_n
                add_holding(r_s, final_name, n_cost, n_shares)
                st.success(f"已成功記錄 {final_name} ({r_s})！")
                st.rerun()
    holdings = load_portfolio()
    if holdings:
        evaluated, summary = evaluate_holdings(holdings)
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("總投入成本", f"${summary['total_cost']:,.0f}")
        s2.metric("當前總市值", f"${summary['total_market_value']:,.0f}")
        s3.metric("未實現總損益", f"${summary['total_profit']:,.0f}", delta=f"{summary['total_profit_pct']}%")
        s4.metric("目前持股檔數", f"{len(evaluated)} 檔")
        
        # 警報彙整與一鍵推播
        alerts = [item for item in evaluated if item.get('is_alert')]
        if alerts:
            st.warning(f"⚠️ 注意！目前有 {len(alerts)} 檔持股觸發風險警報（跌破月線或虧損超過 5%）")
            if st.button("🚨 一鍵推播庫存警報至 Line", type="primary", use_container_width=True):
                msg_lines = ["【台股戰情室 風險警報通知】"]
                for a in alerts:
                    msg_lines.append(f"• {a['name']} ({a['symbol']}): 現價 ${a['current_price']} 損益 {a['profit_pct']}% -> {a['alert_reason']}")
                msg_lines.append(f"總投入成本: ${summary['total_cost']:,.0f} | 市值: ${summary['total_market_value']:,.0f}")
                full_msg = "\n".join(msg_lines)
                ok, msg = send_line_notify(full_msg)
                if ok:
                    st.success("已成功將警報發送至 Line！")
                else:
                    st.error(f"發送失敗：{msg}")
                    
        st.markdown("---")
        for item in evaluated:
            ch, cb = st.columns([5, 1])
            ch.markdown(f"### {item['name']} ({item['symbol']}) — **{item['status_light']}**")
            if cb.button("🗑️ 刪除", key=f"del_port_{item['index']}"):
                remove_holding(item['index'])
                st.rerun()
            col1, col2, col3, col4 = st.columns(4)
            col1.write(f"• 買進成本：**${item['cost']}** ({item['shares']}股)")
            col2.write(f"• 最新現價：**${item['current_price']}**")
            col3.write(f"• 未實現損益：**${item['profit']:,.0f}** (`{item['profit_pct']}%`)")
            col4.write(f"• 20MA防守線：**${item['ma20']}**")
            st.info(f"💡 **操盤決策建議**：{item['advice']}")
            st.markdown("---")
    else:
        st.info("目前無持股記錄，點擊上方展開表單新增！")

# ================= 頁面 8：短線與波段操盤心法 =================
elif menu == "📖 8. 短線與波段操盤心法":
    st.title("📖 台股短線與波段操盤實戰心法")
    st.markdown("""
    ### 🎯 【短線放量突破實戰檢核單】
    1. **大盤環境**：加權指數環境評分必須 >= 40 分，空頭環境全域禁止開倉。
    2. **超額強度 (RS)**：個股近 20 日表現必須強於大盤 (RS > 0)，只打強勢領頭羊。
    3. **型態確認**：帶量突破 20 日最高點（均量 1.5 倍以上），或於前高 2.5% 內窄幅量縮蓄勢。
    4. **嚴禁追高 (Too Extended)**：單日急漲超過 +7% 或偏離前高超標者，嚴禁追價！
    
    ---
    ### 👑 【老王均線最高指導原則】
    * **萬里無雲 (三陽開泰)**：站穩 5MA、10MA、20MA 三線多頭排列，上檔無壓力！
    * **買黑不買紅**：突破後拉回測試 5MA/10MA 守穩之量縮黑K，才是最高盈虧比買點！
    * **出場三部曲**：
      * 跌破 5MA：短線停滯，「先賣一半減碼」！
      * 跌破 10MA / 20MA：生命線失守，「全數清倉，現金為王」！
      * 跌破近 20 日大量 K 棒最低點：主力套牢訊號，無條件止損撤退！
    """)