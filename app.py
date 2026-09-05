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
    analyze_dynamic_market_hot_stocks,
    analyze_custom_pool_stocks,
    analyze_curated_theme_stocks,
    run_ai_deep_analysis,
    analyze_and_rank_pool
)
from custom_pool_manager import load_custom_pool, add_to_custom_pool, remove_from_custom_pool
from portfolio_manager import load_portfolio, add_holding, remove_holding, evaluate_holdings
import config

st.set_page_config(
    page_title=f"{config.APP_TITLE} {config.APP_VERSION}",
    page_icon=config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- 頂級 RWD 深色專業操盤 CSS -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* 專業側邊欄選單優化 */
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
    
    /* 玻璃擬態戰情卡片 */
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
    
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- 側邊欄導航 (更新 TITLE 為 台股戰情室) -----------------
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
        "🔥 1. 熱門焦點與進場評估",
        "🧠 2. AI 個股深度量化診斷",
        "🎯 3. 投信鎖碼波段選股榜",
        "🌐 4. 盤後宏觀與法人籌碼",
        "📈 5. 互動 K 線與指標圖室",
        "💼 6. 庫存管家與防守警報",
        "📖 7. 波段交易紀律與心法"
    ],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 同步刷新數據", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(f"盤後更新：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
st.sidebar.caption("✅ 支援手機 RWD 直式介面操作")

# ================= 頁面 1：熱門焦點與進場評估 =================
if menu == "🔥 1. 熱門焦點與進場評估":
    st.title(f"🔥 市場熱門焦點股與量化進場評估")
    st.caption(f"{config.APP_TITLE} ｜ 核心引擎：{config.APP_VERSION} ｜ 支援動態成交榜、自選題材庫與生技/ETF/AI主流")
    
    tab1, tab2, tab3 = st.tabs([
        "⚡ 分頁 A：全市場動態成交熱門榜",
        "🛠️ 分頁 B：我的自選題材追蹤池",
        "💎 分頁 C：精選產業主流題材庫"
    ])
    
    with tab1:
        st.subheader("⚡ 全市場即時成交爆量熱門股 Top 30")
        with st.spinner("自動掃描全市場成交額榜單並運算量價結構中..."):
            market_hot = analyze_dynamic_market_hot_stocks(limit=30)
            
        if market_hot:
            can_buy_c = sum(1 for x in market_hot if "可以進場" in x['entry_signal'] or "買點浮現" in x['entry_signal'])
            overheat_c = sum(1 for x in market_hot if "極度過熱" in x['entry_signal'])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("今日熱門掃描", f"{len(market_hot)} 檔")
            c2.metric("🟢 浮現買點", f"{can_buy_c} 檔")
            c3.metric("⚠️ 指標過熱", f"{overheat_c} 檔")
            
            st.markdown("#### 🔥 前 6 大成交核心焦點卡片")
            cards = market_hot[:6]
            for i in range(0, len(cards), 3):
                cols = st.columns([1, 1, 1])
                for j in range(3):
                    if i + j < len(cards):
                        it = cards[i + j]
                        with cols[j]:
                            pill_class = "pill-buy" if "可" in it['entry_signal'] or "買" in it['entry_signal'] else ("pill-hot" if "過熱" in it['entry_signal'] else "pill-warn")
                            st.markdown(f"""
                            <div class="rwd-card">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <h3 style="margin:0;">{it['name']} <span style="font-size:0.9rem; color:gray;">({it['symbol']})</span></h3>
                                    <span class="pill {pill_class}">{it['entry_signal'].split(' ')[0]}</span>
                                </div>
                                <h2 style="margin:8px 0; color:#ef4444;">${it['close']} <span style="font-size:1rem; color:#ef4444;">+{it['pct_change']}%</span></h2>
                                <p style="margin:4px 0; font-size:0.85rem; color:#cbd5e1;">💰 成交金額：<b>約 {it['turnover_billion']} 億元</b></p>
                                <p style="margin:4px 0; font-size:0.85rem; color:#cbd5e1;">📊 今日量能：<b>均量 {it['vol_ratio']} 倍</b> ｜ RSI: <b>{it['rsi']}</b></p>
                                <div style="background:rgba(255,255,255,0.03); border-radius:8px; padding:8px; margin-top:8px;">
                                    <span style="font-size:0.82rem; color:#93c5fd;">👉 {it['action_advice']}</span>
                                </div>
                                <p style="margin:8px 0 0 0; font-size:0.82rem; color:#94a3b8;">🛡️ 防守停損參考價：<b>${it['stop_loss']}</b></p>
                            </div>
                            """, unsafe_allow_html=True)
                            
            st.markdown("#### 📋 全市場 Top 30 成交量能詳細清單")
            df_m = pd.DataFrame([
                {
                    '代號': x['symbol'], '名稱': x['name'], '成交金額(億)': x['turnover_billion'],
                    '現價': x['close'], '漲跌幅': f"{x['pct_change']}%", '量能倍數': f"{x['vol_ratio']}x",
                    '進場決策': x['entry_signal'], '防守停損價': x['stop_loss']
                } for x in market_hot
            ])
            st.dataframe(df_m, use_container_width=True)
            
    with tab2:
        st.subheader("🛠️ 我的自選題材追蹤池 (隨意新增/刪除)")
        st.caption("支援直接輸入代號（如 00878, 0050, 6467）或名稱（如 泰合, 仁新），系統自動聯網辨識名稱與量價！")
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
                else:
                    st.error("請填入代號或名稱！")
                    
        custom_pool = load_custom_pool()
        if custom_pool:
            custom_analysis = analyze_custom_pool_stocks(custom_pool)
            for item in custom_analysis:
                with st.container():
                    c_head, c_del = st.columns([5, 1])
                    with c_head:
                        st.markdown(f"### {item['name']} ({item['symbol']}) <span class='pill pill-blue'>{item['tag']}</span> `{item['entry_signal']}`", unsafe_allow_html=True)
                    with c_del:
                        if st.button("🗑️ 移出", key=f"del_c_{item['symbol']}"):
                            remove_from_custom_pool(item['symbol'])
                            st.rerun()
                    inf1, inf2, inf3, inf4 = st.columns(4)
                    inf1.metric("現價", f"${item['close']}", f"{item['pct_change']}%")
                    inf2.write(f"• 今日量能：**均量 {item['vol_ratio']} 倍**")
                    inf3.write(f"• 5MA 乖離率：**{item['bias_5ma']}%**")
                    inf4.markdown(f"🛡️ **關鍵防守價**：`${item['stop_loss']}`")
                    st.info(f"👉 **量化操盤建議**：{item['action_advice']}")
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
                '現價': x['close'], '漲跌幅': f"{x['pct_change']}%", '量能倍數': f"{x['vol_ratio']}x",
                '進場決策': x['entry_signal'], '防守停損價': x['stop_loss']
            } for x in curated_list
        ])
        st.dataframe(df_c, use_container_width=True)

# ================= 頁面 2：AI 個股深度量化診斷 (支援 ETF 與所有個股代號) =================
elif menu == "🧠 2. AI 個股深度量化診斷":
    st.title("🧠 個股 / ETF AI 深度走勢與買盤操盤診斷室")
    st.caption("支援輸入上市櫃代號 (如 6467, 2330)、熱門 ETF (如 00878, 0050, 0056) 或中文名稱 (如 泰合, 仁新)")
    
    col_in1, col_in2 = st.columns([3, 1])
    with col_in1:
        query_input = st.text_input("請輸入台股/ETF 代號或名稱：", value="00878").strip()
    with col_in2:
        st.write("")
        st.write("")
        st.button("🚀 啟動 AI 深度分析", type="primary", use_container_width=True)
        
    if query_input:
        with st.spinner(f"AI 操盤引擎正在全面掃描『{query_input}』之技術面與消息..."):
            data, err = run_ai_deep_analysis(query_input)
            
        if err:
            st.error(err)
        else:
            st.markdown(f"""
            <div class="rwd-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h2 style="margin:0;">{data['name']} <span style="font-size:1.2rem; color:gray;">({data['symbol']})</span></h2>
                        <span class="pill pill-blue">AI 量化診斷報告</span>
                    </div>
                    <div style="text-align:right;">
                        <h1 style="margin:0; color:#ef4444;">${data['close']}</h1>
                        <span style="color:#ef4444; font-weight:600;">+{data['pct_change']}%</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # AI 決策核心
            st.markdown(f"### 🎯 AI 操盤行動決策：**{data['ai_verdict']}**")
            p1, p2, p3, p4 = st.columns(4)
            p1.success(f"📥 **建議進場區間**\n\n**{data['entry_zone']}**")
            p2.error(f"🛑 **波段防守停損價**\n\n**`${data['stop_loss']}`**")
            p3.info(f"🎯 **短波段目標價**\n\n**`${data['target']}`**")
            p4.warning(f"⚖️ **風險報酬比 (R/R)**\n\n**{data['rr']} : 1**")
            
            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown("#### 🔍 主力買盤力道與量能")
                st.write(f"• **當前買盤力道**：{data['buying_power']}")
                st.write(f"• **量價結構診斷**：{data['vol_structure']}")
                st.write(f"• **量能放大倍數**：5日均量之 **{data['vol_ratio']} 倍**")
            with c_right:
                st.markdown("#### 📈 均線位階與多空架構")
                st.write(f"• 5MA：**${data['ma5']}** ｜ 10MA：**${data['ma10']}**")
                st.write(f"• 20MA (生命線)：**${data['ma20']}** ｜ 60MA：**${data['ma60']}**")
                if data['close'] > data['ma20']:
                    st.success("✔ 股價/淨值站穩 20MA 生命線之上，多方結構完整。")
                else:
                    st.error("✖ 股價/淨值跌破 20MA 月線生命線，短中期偏空整理。")
                    
            st.markdown("---")
            st.markdown(f"#### 📰 【{data['name']}】最新重大財經新聞與催化劑")
            if data['news']:
                for n in data['news']:
                    st.markdown(f"• [{n['title']}]({n['link']}) — <small style='color:gray'>{n['date']}</small>", unsafe_allow_html=True)
            else:
                st.write("近期查無重大突發新聞。")

# ================= 頁面 3：投信鎖碼波段選股榜 =================
elif menu == "🎯 3. 投信鎖碼波段選股榜":
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

# ================= 頁面 4：盤後宏觀與法人籌碼 =================
elif menu == "🌐 4. 盤後宏觀與法人籌碼":
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

# ================= 頁面 5：互動 K 線與指標圖室 (支援 ETF 與所有個股) =================
elif menu == "📈 5. 互動 K 線與指標圖室":
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

# ================= 頁面 6：庫存管家與防守警報 =================
elif menu == "💼 6. 庫存管家與防守警報":
    st.title("💼 我的持股庫存管家與即時風險警報")
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

# ================= 頁面 7：波段交易紀律與心法 =================
elif menu == "📖 7. 波段交易紀律與心法":
    st.title("📖 台股波段動能操盤手實戰心法")
    st.markdown("""
    ### 🎯 【波段標準進場檢核單 (Checklist)】
    * [ ] **大盤多空**：加權與櫃買指數雙雙站穩 20MA 生命線。
    * [ ] **題材催化**：具備高市場關注度題材（如高人氣高股息ETF、生技拆股換發、AI水冷散熱、CPO矽光子）。
    * [ ] **量價確認**：放量突破平台整理，或量縮回測 5MA/10MA 支撐不破。
    * [ ] **嚴格停損**：收盤跌破 20MA 或單筆虧損達 **-5% 至 -7%** 無條件停損離場，絕不凹單攤平！
    """)
