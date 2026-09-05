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
    page_title=config.APP_TITLE,
    page_icon=config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stMetric {
        background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 12px 16px;
    }
    .badge-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-right: 6px;
        background-color: rgba(30, 144, 255, 0.2);
        color: #60a5fa;
        border: 1px solid rgba(96, 165, 250, 0.4);
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.title(f"{config.APP_ICON} 戰情室功能導航")
menu = st.sidebar.radio(
    "請選擇分析模組：",
    [
        "🔥 1. 最近熱門股與進場分析 (3合1升級版)",
        "🤖 2. 個股 AI 深度走勢與買盤診斷",
        "🎯 3. 法人動能選股雷達 (Top 5 & 總榜)",
        "🌐 4. 盤後宏觀與三大法人籌碼",
        "🔍 5. 專業互動 K 線圖室 (台股配色)",
        "💼 6. 我的庫存管家與停損警報",
        "📖 7. 波段交易紀律操盤心法"
    ]
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 一鍵強制同步/刷新最新數據"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(f"系統時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.sidebar.info("💡 **台股短波段操盤鐵律**：\n• 跌破 20MA 或單筆虧損達 5% 嚴格停損。\n• 沿 10MA 抱單，收盤跌破分批收網。\n• 只做量縮守支撐與突破第一根，不追超漲爆量黑棒。")

# 頁面 1：熱門股與進場分析 (3合1版)
if menu == "🔥 1. 最近熱門股與進場分析 (3合1升級版)":
    st.title("🔥 市場熱門焦點股與量化進場評估")
    st.markdown("結合「**全市場真實成交金額排行**」、「**使用者自訂編輯題材池**」與「**生技/AI核心族群庫**」，即時評估當前動能與進場時機。")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs([
        "⚡ 分頁 A：全市場動態成交熱門榜 (非固定池，自動掃描)",
        "🛠️ 分頁 B：自訂/編輯題材追蹤池 (隨意增減標的)",
        "💎 分頁 C：精選主流題材庫 (生技/AI/散熱/矽光子)"
    ])
    
    with tab1:
        st.subheader("⚡ 全市場即時成交金額爆量熱門股 Top 30")
        st.caption("直接向證券交易所抓取當前市場成交金額最大、人氣最爆棚的活躍標的，自動運算『是否可以進場』。")
        with st.spinner("正在自動掃描全市場成交額榜單並運算量價結構..."):
            market_hot = analyze_dynamic_market_hot_stocks(limit=30)
        if market_hot:
            c1, c2, c3 = st.columns(3)
            can_buy_c = sum(1 for x in market_hot if "可以進場" in x['entry_signal'] or "買點浮現" in x['entry_signal'])
            overheat_c = sum(1 for x in market_hot if "極度過熱" in x['entry_signal'])
            c1.metric("即時活躍個股", f"{len(market_hot)} 檔")
            c2.metric("🟢 浮現買點 / 可進場", f"{can_buy_c} 檔")
            c3.metric("⚠️ 指標過熱 / 嚴禁追高", f"{overheat_c} 檔")
            st.markdown("#### 🔥 人氣成交額前 6 大焦點股決策卡")
            cards = market_hot[:6]
            for i in range(0, len(cards), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i + j < len(cards):
                        it = cards[i + j]
                        with cols[j]:
                            st.markdown(f"### {it['name']} ({it['symbol']})")
                            st.metric("收盤價", f"${it['close']}", f"{it['pct_change']}%")
                            st.markdown(f"**成交金額**：約 `{it['turnover_billion']} 億元`")
                            st.markdown(f"**進場評估**：`{it['entry_signal']}`")
                            st.write(f"• 今日量能：**5日均量之 {it['vol_ratio']} 倍**")
                            st.write(f"• 5MA乖離：**{it['bias_5ma']}%** | RSI：**{it['rsi']}**")
                            st.info(f"👉 **建議**：{it['action_advice']}")
                            st.markdown(f"🛡️ **參考防守價**：`${it['stop_loss']}`")
                            st.markdown("---")
            st.markdown("#### 📋 全市場 Top 30 成交量能詳細總清單")
            df_m = pd.DataFrame([
                {
                    '代號': x['symbol'], '名稱': x['name'], '成交金額(億)': x['turnover_billion'],
                    '現價': x['close'], '漲跌幅': f"{x['pct_change']}%", '量能倍數': f"{x['vol_ratio']}x",
                    '進場決策': x['entry_signal'], '操盤具體建議': x['action_advice'], '防守停損價': x['stop_loss']
                } for x in market_hot
            ])
            st.dataframe(df_m, use_container_width=True)
            
    with tab2:
        st.subheader("🛠️ 我的自選題材追蹤池 (隨意新增/刪除)")
        st.caption("你可以將自己關注的任何股票（如 6467 泰合生技、6696 仁新、3017 奇鋐）加入此清單，系統每天自動為你診斷進場點位。")
        with st.expander("➕ 新增股票至自選追蹤池", expanded=False):
            f1, f2, f3, f4 = st.columns(4)
            in_sym = f1.text_input("股票代號 (如 6467, 6696)", key="custom_sym")
            in_name = f2.text_input("股票名稱 (如 泰合生技, 仁新)", key="custom_name")
            in_tag = f3.text_input("族群標籤 (如 生技新藥, AI水冷)", key="custom_tag")
            in_note = f4.text_input("自訂備註 (如 留意拆股突破)", key="custom_note")
            if st.button("確認加入自選池"):
                if in_sym:
                    res_sym, res_name = resolve_stock(in_sym)
                    real_name = in_name if in_name else res_name
                    ok, msg = add_to_custom_pool(res_sym, real_name, in_tag, in_note)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error("請至少填入股票代號！")
        custom_pool = load_custom_pool()
        if custom_pool:
            custom_analysis = analyze_custom_pool_stocks(custom_pool)
            st.markdown("#### 📌 目前追蹤之自選標的進場狀態")
            for item in custom_analysis:
                with st.container():
                    c_head, c_del = st.columns([6, 1])
                    with c_head:
                        st.markdown(f"### {item['name']} ({item['symbol']}) — <span class='badge-pill'>{item['tag']}</span> `{item['entry_signal']}`", unsafe_allow_html=True)
                    with c_del:
                        if st.button("🗑️ 移出", key=f"del_c_{item['symbol']}"):
                            remove_from_custom_pool(item['symbol'])
                            st.rerun()
                    inf1, inf2, inf3, inf4 = st.columns(4)
                    inf1.metric("現價", f"${item['close']}", f"{item['pct_change']}%")
                    inf2.write(f"• 今日量能：**均量 {item['vol_ratio']} 倍**")
                    inf3.write(f"• 5MA 乖離率：**{item['bias_5ma']}%**")
                    inf4.markdown(f"🛡️ **關鍵防守價**：`${item['stop_loss']}`")
                    if item['note']:
                        st.caption(f"📝 **自訂備註**：{item['note']}")
                    st.info(f"👉 **量化操盤建議**：{item['action_advice']}")
                    st.markdown("---")
        else:
            st.info("目前自選池為空，請點擊上方『新增股票至自選追蹤池』開始建立你的專屬觀察清單！")

    with tab3:
        st.subheader("💎 市場核心題材庫 (生技拆股、AI、CPO、設備、重電)")
        st.caption("涵蓋仁新（6696 1拆10換發新股）、泰合生技、藥華藥、美時等主流生技與科技熱門股。")
        with st.spinner("計算精選產業題材量價動能中..."):
            curated_list = analyze_curated_theme_stocks()
        df_c = pd.DataFrame([
            {
                '代號': x['symbol'], '名稱': x['name'], '族群題材': x['theme'],
                '現價': x['close'], '漲跌幅': f"{x['pct_change']}%", '量能倍數': f"{x['vol_ratio']}x",
                '進場決策': x['entry_signal'], '操盤具體建議': x['action_advice'], '防守停損價': x['stop_loss']
            } for x in curated_list
        ])
        st.dataframe(df_c, use_container_width=True)

# 頁面 2：個股 AI 深度診斷室
elif menu == "🤖 2. 個股 AI 深度走勢與買盤診斷":
    st.title("🤖 個股 AI 深度走勢與買盤操盤診斷室")
    st.markdown("支援**直接輸入股票名稱（如：泰合、仁新、台積電、奇鋐）或 4 碼代號（如：6467、6696、2330）**，由 AI 全面解析多空走勢、主力買盤結構與進出場點位。")
    st.markdown("---")
    
    col_in1, col_in2 = st.columns([3, 1])
    with col_in1:
        query_input = st.text_input(
            "請輸入台股名稱或 4 碼代號：",
            value="泰合",
            help="支援生技股如『泰合』(6467)、『仁新』(6696)、『藥華藥』(6446) 或電子權值股『台積電』(2330) 等全台股"
        ).strip()
    with col_in2:
        st.write("")
        st.write("")
        st.button("🚀 啟動 AI 深度分析", type="primary")
        
    if query_input:
        with st.spinner(f"AI 操盤引擎正在全面掃描『{query_input}』之籌碼量能、均線結構與最新即時新聞..."):
            data, err = run_ai_deep_analysis(query_input)
            
        if err:
            st.error(err)
        else:
            st.subheader(f"📊 【{data['name']} ({data['symbol']})】AI 深度操盤評估報告")
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("最新收盤價", f"${data['close']}", f"{data['pct_change']}%")
            r2.metric("當日振幅空間", f"${data['low']} ~ ${data['high']}")
            r3.metric("量能放大倍數", f"5日均量之 {data['vol_ratio']} 倍")
            r4.metric("14日 RSI 動能", f"{data['rsi']}")
            st.markdown("---")
            
            st.markdown(f"### 🎯 AI 操盤行動決策：**{data['ai_verdict']}**")
            p1, p2, p3, p4 = st.columns(4)
            p1.success(f"📥 **建議進場區間**\n\n**{data['entry_zone']}**")
            p2.error(f"🛑 **波段防守停損價**\n\n**`${data['stop_loss']}`**")
            p3.info(f"🎯 **短波段目標價**\n\n**`${data['target']}`**")
            p4.warning(f"⚖️ **風險報酬比 (R/R)**\n\n**{data['rr']} : 1**")
            st.markdown("---")
            
            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown("#### 🔍 主力買盤力道與籌碼剖析")
                st.write(f"• **當前買盤力道**：{data['buying_power']}")
                st.write(f"• **量價結構診斷**：{data['vol_structure']}")
                st.write(f"• **今日成交量**：約 {int(data['vol']):,} 股")
                st.info("💡 **主力買盤判讀訣竅**：若成交量為 5 日均量 1.4 倍以上且拉出長紅，為大戶強勢敲進訊號；若高檔出大量卻收長黑，則為主力調節出貨警戒！")
            with c_right:
                st.markdown("#### 📈 均線位階與多空架構")
                st.write(f"• 5MA (短線動能線)：**${data['ma5']}**")
                st.write(f"• 10MA (雙週線)：**${data['ma10']}**")
                st.write(f"• 20MA (月線生命線)：**${data['ma20']}**")
                st.write(f"• 60MA (季線保護傘)：**${data['ma60']}**")
                if data['close'] > data['ma20']:
                    st.success("✔ 股價站穩 20MA 生命線之上，波段多方控盤結構完整。")
                else:
                    st.error("✖ 股價跌破 20MA 月線生命線，短中期偏空整理，未放量站回前切忌急於低接。")
            st.markdown("---")
            st.markdown(f"#### 📰 【{data['name']}】最新重大財經新聞與催化劑")
            if data['news']:
                for n in data['news']:
                    st.markdown(f"• [{n['title']}]({n['link']}) — <small style='color:gray'>{n['date']}</small>", unsafe_allow_html=True)
            else:
                st.write("近期查無重大突發新聞報導。")

# 頁面 3：法人動能選股雷達
elif menu == "🎯 3. 法人動能選股雷達 (Top 5 & 總榜)":
    st.title("🎯 法人動能波段選股雷達")
    st.markdown("連線證交所全市場**投信真實買超鎖碼前 30 名**，依據均線、量能、突破位階挑出 Top 5。")
    st.markdown("---")
    @st.cache_data(ttl=1200)
    def cached_rankings():
        return analyze_and_rank_pool(limit=30)
    with st.spinner("抓取最新盤後投信買賣超排行榜中..."):
        all_ranks = cached_rankings()
    top5 = all_ranks[:5]
    if top5:
        st.subheader("🔥 投信波段鎖碼精選 Top 5 (持股 1~2 週)")
        cols = st.columns(len(top5))
        for i, s in enumerate(top5):
            with cols[i]:
                st.markdown(f"#### {s['name']} ({s['symbol']})")
                st.metric("現價", f"${s['close']}", f"{s['pct_change']}%")
                st.progress(s['score'] / 100)
                st.caption(f"評分：**{s['score']} / 100**")
                st.markdown(f"🛡️ 防守價：`${s['stop_loss']}`")
                st.markdown(f"🎯 目標價：`${s['target_price']}`")
                with st.expander("入選理由"):
                    for sig in s['signals']:
                        st.write(f"• {sig}")
        st.markdown("---")
        st.subheader("📋 投信買超鎖碼評分總榜單 (Top 30)")
        df_display = pd.DataFrame([
            {
                '代號': item['symbol'], '名稱': item['name'], '收盤價': item['close'],
                '漲跌幅(%)': f"{item['pct_change']}%", '投信買超(張)': f"{item['trust_vol']:,}",
                '量化分數': item['score'], '20MA月線': item['ma20'], '建議防守價': item['stop_loss'],
                '強勢標籤': " / ".join(item['tags'])
            } for item in all_ranks
        ])
        st.dataframe(df_display, use_container_width=True)
    else:
        st.warning("今日無符合高評分門檻標的。")

# 頁面 4：盤後宏觀與三大法人籌碼
elif menu == "🌐 4. 盤後宏觀與三大法人籌碼":
    st.title("🌐 盤後宏觀總覽與三大法人資金風向標")
    macro = get_macro_overview()
    funds = get_institutional_investors_summary()
    st.subheader("📊 國際連動與台美核心指數")
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
    st.subheader("💰 台灣證交所三大法人當日買賣超 (億元)")
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("外資買賣超", f"{funds['外資']} 億", delta=f"{funds['外資']}")
    f2.metric("投信買賣超", f"{funds['投信']} 億", delta=f"{funds['投信']}")
    f3.metric("自營商買賣超", f"{funds['自營商']} 億", delta=f"{funds['自營商']}")
    f4.metric("三大法人總計", f"{funds['合計']} 億", delta=f"{funds['合計']}")

# 頁面 5：專業互動 K 線圖室 (台股紅漲綠跌)
elif menu == "🔍 5. 專業互動 K 線圖室 (台股配色)":
    st.title("🔍 專業互動 K 線圖室 (標準台股 紅漲 🔴 / 綠跌 🟢)")
    col_k1, col_k2 = st.columns([3, 1])
    with col_k1:
        sym_in = st.text_input("請輸入欲檢視之股票代號或名稱：", value="6467", help="例如 6467 (泰合), 6696 (仁新), 2330 (台積電)").strip()
    with col_k2:
        st.write("")
        st.write("")
        st.button("更新線圖")
    if sym_in:
        real_sym, real_name = resolve_stock(sym_in)
        df = get_stock_history(real_sym, period='4mo')
        if not df.empty:
            st.markdown(f"##### 📈 【{real_name} ({real_sym})】日 K 線與均線布林通道系統")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing_line_color='#ef4444', decreasing_line_color='#22c55e',
                name='K線'
            ))
            fig.add_trace(go.Scatter(x=df.index, y=df['5MA'], line=dict(color='#f59e0b', width=1.5), name='5MA(週線)'))
            fig.add_trace(go.Scatter(x=df.index, y=df['10MA'], line=dict(color='#a855f7', width=1.5), name='10MA(雙週線)'))
            fig.add_trace(go.Scatter(x=df.index, y=df['20MA'], line=dict(color='#3b82f6', width=2.2), name='20MA(生命線)'))
            fig.add_trace(go.Scatter(x=df.index, y=df['60MA'], line=dict(color='#10b981', width=1.5), name='60MA(季線)'))
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], line=dict(color='gray', width=1, dash='dash'), name='布林上軌'))
            fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], line=dict(color='gray', width=1, dash='dash'), name='布林下軌'))
            fig.update_layout(
                xaxis_rangeslider_visible=False, height=520,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"查無 {real_sym} 之歷史數據。")

# 頁面 6：我的庫存管家與停損警報
elif menu == "💼 6. 我的庫存管家與停損警報":
    st.title("💼 我的持股庫存管家與即時風險警報")
    with st.expander("➕ 新增持股記錄", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        n_sym = c1.text_input("股票代號 (如 6467, 6696)")
        n_name = c2.text_input("股票名稱 (如 泰合生技, 仁新)")
        n_cost = c3.number_input("買進成本價格", min_value=1.0, value=100.0, step=1.0)
        n_shares = c4.number_input("股數 (1張=1000股)", min_value=1, value=1000, step=100)
        if st.button("確認加入庫存部位"):
            if n_sym:
                r_s, r_n = resolve_stock(n_sym)
                final_name = n_name if n_name else r_n
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
            ch, cb = st.columns([6, 1])
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
        st.info("目前無持股記錄，請點擊上方新增持股開始部位管理。")

# 頁面 7：波段交易紀律操盤心法
elif menu == "📖 7. 波段交易紀律操盤心法":
    st.title("📖 台股波段動能操盤手實戰心法")
    st.markdown("""
    ### 🎯 【波段標準進場檢核單 (Checklist)】
    * [ ] **大盤多空**：加權與櫃買指數雙雙站穩 20MA 生命線。
    * [ ] **題材催化**：具備高市場關注度題材（如生技拆股換發、AI水冷散熱、CPO矽光子）。
    * [ ] **量價確認**：放量突破平台整理，或量縮回測 5MA/10MA 支撐不破。
    * [ ] **嚴格停損**：收盤跌破 20MA 或單筆虧損達 **-5% 至 -7%** 無條件停損離場，絕不凹單攤平！
    """)
