import os
import json
import logging
from dotenv import load_dotenv, dotenv_values

# 找到 .env 的絕對路徑（與 gemini_engine.py 同目錄）
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

# 啟動時載入一次（override=True 確保 .env 蓋過系統環境變數）
load_dotenv(dotenv_path=_ENV_PATH, override=True)

logger = logging.getLogger(__name__)

def get_api_key(custom_key=None):
    """
    讀取 API Key 優先順序：
    1. 明確傳入的 custom_key
    2. os.environ（含 load_dotenv 載入的值，以及前端 Save 後即時寫入的值）
    3. Streamlit Cloud Secrets (st.secrets)
    4. 實體 .env 檔案直接解析
    """
    if custom_key and str(custom_key).strip():
        return str(custom_key).strip()
    k = os.environ.get('GEMINI_API_KEY', '').strip()
    if k:
        return k
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            sec_k = str(st.secrets["GEMINI_API_KEY"]).strip()
            if sec_k:
                os.environ['GEMINI_API_KEY'] = sec_k
                return sec_k
    except Exception:
        pass
    if os.path.exists(_ENV_PATH):
        try:
            with open(_ENV_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('GEMINI_API_KEY='):
                        val = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
                        if val:
                            os.environ['GEMINI_API_KEY'] = val
                            return val
        except Exception:
            pass
    return ""

def save_api_key(new_key: str) -> bool:
    """將 API Key 儲存至根目錄 .env 實體檔案與環境變數"""
    try:
        clean_key = str(new_key).strip()
        lines = []
        if os.path.exists(_ENV_PATH):
            with open(_ENV_PATH, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        key_found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith('GEMINI_API_KEY='):
                new_lines.append(f'GEMINI_API_KEY={clean_key}\n')
                key_found = True
            else:
                new_lines.append(line)
        if not key_found:
            new_lines.append(f'GEMINI_API_KEY={clean_key}\n')
        with open(_ENV_PATH, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        os.environ['GEMINI_API_KEY'] = clean_key
        return True
    except Exception as e:
        logger.error(f"Failed to save GEMINI_API_KEY: {e}")
        return False

def clear_api_key() -> bool:
    """從 .env 檔案與環境變數中清除 API Key"""
    try:
        if os.path.exists(_ENV_PATH):
            with open(_ENV_PATH, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                if line.strip().startswith('GEMINI_API_KEY='):
                    new_lines.append('GEMINI_API_KEY=\n')
                else:
                    new_lines.append(line)
            with open(_ENV_PATH, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']
        return True
    except Exception as e:
        logger.error(f"Failed to clear GEMINI_API_KEY: {e}")
        return False

def _call_gemini(prompt, custom_key=None, json_mode=True, temperature=0.2):
    """
    統一 Gemini API 呼叫，依序嘗試模型，失敗回傳 None
    """
    api_key = get_api_key(custom_key)
    if not api_key:
        logger.warning('No GEMINI_API_KEY found')
        return None
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        cfg = types.GenerateContentConfig(temperature=temperature)
        if json_mode:
            cfg.response_mime_type = 'application/json'
        for m in ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']:
            try:
                resp = client.models.generate_content(model=m, contents=prompt, config=cfg)
                if resp and resp.text:
                    return json.loads(resp.text) if json_mode else resp.text
            except Exception as em:
                logger.warning(f'Model {m} failed: {em}')
                continue
        return None
    except Exception as e:
        logger.error(f'Gemini call failed: {e}')
        return None

# ─────────────────────────────────────────────────────────────────────
# 1. 分析師影音內容解析（原有功能保留）
# ─────────────────────────────────────────────────────────────────────

def analyze_guru_content_with_gemini(guru_name, video_title, transcript_or_desc, custom_key=None):
    prompt = f"""你是精通台灣股票的專業操盤手。請深度解析名師「{guru_name}」的最新影音內容：
標題：{video_title}
內容摘要：
{transcript_or_desc[:4500]}

請嚴格以繁體中文（台灣習慣用語）提煉，並回傳標準JSON格式：
{{
  "guru_summary": "名師對本集大盤多空或結論摘要（60~100字）",
  "market_stance": "看多 / 看空 / 觀望 / 震盪整理",
  "mentioned_stocks": [
    {{
      "symbol": "股票代號（4碼數字，無明確代號則填空字串）",
      "name": "股票名稱",
      "stance": "看多 / 看空 / 觀望 / 買黑不買紅",
      "guru_quote": "名師原話關鍵論點摘錄（50字內）",
      "action_trigger": "建議進場或觀察條件",
      "defense_price": "建議防守或停損價位",
      "confidence": "高 / 中 / 低"
    }}
  ]
}}"""
    return _call_gemini(prompt, custom_key=custom_key)

# ─────────────────────────────────────────────────────────────────────
# 2. 論壇情緒分析（原有功能保留）
# ─────────────────────────────────────────────────────────────────────

def analyze_forum_sentiment_with_gemini(topics_list, custom_key=None):
    summaries = []
    for t in topics_list[:15]:
        stks = ', '.join(t.get('stocks', []))
        src = t.get('source', 'CMoney')
        txt = t.get('text', '')
        summaries.append(f'[{src}]【標的：{stks}】：{txt}')
    context_text = '\n---\n'.join(summaries)

    prompt = f"""你是專精台股籌碼與散戶心理學的操盤分析師。
以下是台灣股市論壇（CMoney 同學會、PTT Stock 版）的熱門發文：

{context_text}

請進行【散戶情緒溫度計與買賣篩選分析】，並回傳JSON格式：
{{
  "overall_sentiment": "極度熱絡 / 追高恐慌 / 分歧震盪 / 逢低抄底 / 悲觀停損",
  "sentiment_score": 70,
  "crowd_psychology": "散戶當前心理狀態總結（約80字）",
  "market_regime_impact": "對短線大盤的警訊或契機（約40字）",
  "contrarian_warning": "逆向思考提示（如散戶一面倒看多時提示小心，約40字）",
  "hot_stocks_analysis": [
    {{
      "stock_name": "股票名稱",
      "symbol": "股票代號（4碼數字，無明確則留空）",
      "retail_sentiment": "一面倒看多 / 偏空唱衰 / 意見分歧",
      "sentiment_score": 80,
      "ai_trading_advice": "可逢低承接 / 嚴禁追高 / 跌破停損觀望 / 波段續抱",
      "key_reason": "分析原因（60字內）",
      "risk_level": "高 / 中 / 低"
    }}
  ]
}}"""
    return _call_gemini(prompt, custom_key=custom_key)

# ─────────────────────────────────────────────────────────────────────
# 3. 今日作戰結論整合器（新增核心功能）
# ─────────────────────────────────────────────────────────────────────

def generate_daily_battle_plan(
    market_regime,
    guru_insights_list,
    forum_sentiment,
    night_radar=None,
    custom_key=None
):
    """
    整合【大盤環境】+【名師觀點】+【論壇情緒】+【夜盤風向】
    輸出今日作戰結論：倉位建議 + 今日可進場標的 + 今日迴避標的
    
    參數：
      market_regime: dict，calculate_market_regime() 的結果
      guru_insights_list: list of dict，各頻道 AI 解析結果
      forum_sentiment: dict，analyze_forum_sentiment_with_gemini() 的結果
      night_radar: dict，get_night_session_radar() 的結果（可選）
    """
    # ── 整理大盤資訊 ─────────────────────────
    regime_summary = (
        f"大盤短線環境評分：{market_regime.get('score', '?')}/100，"
        f"狀態：{market_regime.get('status', '?')}，"
        f"描述：{market_regime.get('desc', '')}"
    )

    # ── 整理夜盤資訊 ─────────────────────────
    night_summary = ""
    if night_radar:
        wtx = night_radar.get('wtx', {})
        tsm = night_radar.get('tsm', {})
        nq = night_radar.get('nq', {})
        impact = night_radar.get('impact_pts', 0)
        sentiment_lbl = night_radar.get('gap_sentiment', '')
        night_summary = (
            f"台指期夜盤：{wtx.get('price','?')} ({wtx.get('pct',0):+.2f}%)，"
            f"台積電ADR：${tsm.get('price',0):.2f} ({tsm.get('pct',0):+.2f}%)，"
            f"NQ期貨：{nq.get('price',0):,.0f} ({nq.get('pct',0):+.2f}%)，"
            f"次日跳空估算：{impact:+.0f}點，情緒：{sentiment_lbl}"
        )

    # ── 整理名師觀點 ─────────────────────────
    guru_parts = []
    all_mentioned_stocks = []
    for g in guru_insights_list:
        if not g or not isinstance(g, dict):
            continue
        name = g.get('guru_name', '分析師')
        analysis = g.get('ai_analysis', {})
        if not analysis:
            continue
        summary = analysis.get('guru_summary', '')
        stance = analysis.get('market_stance', '觀望')
        stocks = analysis.get('mentioned_stocks', [])
        guru_parts.append(f"【{name}】大盤觀點：{stance}。摘要：{summary}")
        for s in stocks:
            s['guru_name'] = name
            all_mentioned_stocks.append(s)

    guru_text = '\n'.join(guru_parts) if guru_parts else "今日暫無名師影音資料"

    # ── 整理論壇情緒 ─────────────────────────
    forum_text = ""
    if forum_sentiment and isinstance(forum_sentiment, dict):
        forum_text = (
            f"整體散戶情緒：{forum_sentiment.get('overall_sentiment','?')}，"
            f"情緒分數：{forum_sentiment.get('sentiment_score','?')}/100，"
            f"逆向提醒：{forum_sentiment.get('contrarian_warning','')}"
        )
    else:
        forum_text = "今日論壇資料暫時無法取得"

    # ── 組合 Prompt ─────────────────────────
    stocks_json = json.dumps(all_mentioned_stocks[:10], ensure_ascii=False)
    prompt = f"""你是台股短線操盤 AI 顧問，請整合以下所有市場資訊，給出今日作戰結論。

【今日大盤環境】
{regime_summary}

【夜盤跨市場資訊】
{night_summary if night_summary else '暫無夜盤資料'}

【名師今日觀點】
{guru_text}

【名師點名標的（JSON）】
{stocks_json}

【論壇散戶情緒】
{forum_text}

請以繁體中文（台灣習慣用語）回傳 JSON 格式的今日作戰結論：
{{
  "overall_market_view": "今日大盤短線傾向（多 / 空 / 震盪整理 / 盤整待突破）",
  "guru_consensus": "名師共識（看多 / 看空 / 分歧 / 無最新影音）",
  "forum_warning": "論壇情緒給短線操作的警示（約50字）",
  "position_advice": "今日建議倉位（滿倉 / 七成倉 / 半倉 / 三成倉 / 空倉）",
  "position_reason": "倉位建議原因（約60字）",
  "battle_summary": "今日一句話作戰總結（50字內，精準有力）",
  "entry_candidates": [
    {{
      "symbol": "股票代號",
      "name": "股票名稱",
      "guru": "來自哪位名師",
      "entry_condition": "進場條件（約40字）",
      "stop_loss_hint": "停損參考",
      "confidence": "高 / 中"
    }}
  ],
  "avoid_list": [
    {{
      "symbol": "股票代號或留空",
      "name": "標的名稱",
      "reason": "迴避原因（約30字）"
    }}
  ],
  "key_watch_points": ["今日需重點觀察的事項，最多3點"]
}}"""
    return _call_gemini(prompt, custom_key=custom_key, json_mode=True, temperature=0.15)
