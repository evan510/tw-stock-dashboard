import os
import json
import logging
from dotenv import load_dotenv
import data_cache

load_dotenv()
logger = logging.getLogger(__name__)

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

def get_api_key(custom_key=None):
    if custom_key and str(custom_key).strip():
        return str(custom_key).strip()
    
    # 1. 環境變數優先
    k = os.environ.get('GEMINI_API_KEY', '').strip()
    if k:
        return k
        
    # 2. Streamlit Secrets (若在 Streamlit Cloud 部署)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            sec_k = str(st.secrets["GEMINI_API_KEY"]).strip()
            if sec_k:
                os.environ['GEMINI_API_KEY'] = sec_k
                return sec_k
    except Exception:
        pass
        
    # 3. 實體 .env 檔案直接解析
    if os.path.exists(ENV_PATH):
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            os.environ['GEMINI_API_KEY'] = val
                            return val
        except Exception as e:
            logger.warning(f"Error reading .env: {e}")
            
    return ""

def save_api_key(new_key: str) -> bool:
    """將 API Key 儲存至根目錄 .env 實體檔案與環境變數"""
    try:
        clean_key = str(new_key).strip()
        lines = []
        key_found = False
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        new_lines = []
        for line in lines:
            if line.strip().startswith("GEMINI_API_KEY="):
                new_lines.append(f"GEMINI_API_KEY={clean_key}\n")
                key_found = True
            else:
                new_lines.append(line)
        if not key_found:
            new_lines.append(f"GEMINI_API_KEY={clean_key}\n")
            
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        os.environ['GEMINI_API_KEY'] = clean_key
        return True
    except Exception as e:
        logger.error(f"Failed to save GEMINI_API_KEY: {e}")
        return False

def clear_api_key() -> bool:
    """從 .env 檔案與環境變數中清除 API Key"""
    try:
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                if line.strip().startswith("GEMINI_API_KEY="):
                    new_lines.append("GEMINI_API_KEY=\n")
                else:
                    new_lines.append(line)
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        return True
    except Exception as e:
        logger.error(f"Failed to clear GEMINI_API_KEY: {e}")
        return False

def analyze_guru_content_with_gemini(guru_name, video_title, transcript_or_desc, custom_key=None):
    api_key = get_api_key(custom_key)
    if not api_key:
        logger.warning('No GEMINI_API_KEY found')
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        prompt = f"""你是精通台灣股票的專業操盤手。請深度解析名師「{guru_name}」的最新影音內容：
標題：{video_title}
內容摘要：
{transcript_or_desc[:4500]}

請厷格以繁體中文（台灣習慣用語）提煉，並回傳標準JSON格式：
{
  "guru_summary": "名師對本集大盤多空或結論摘要（60~100字）",
  "mentioned_stocks": [
    {
      "symbol": "股票代號（4碼數字，無明確代號則填空字串）",
      "name": "股票名稱",
      "stance": "看多 / 看空 / 觀望 / 買黑不買紅",
      "guru_quote": "名師原話關鍵論點摘錄（50字內）",
      "action_trigger": "建議進場或觀察條件",
      "defense_price": "建議防守或停�%8損價位",
      "confidence": "高 / 中 / 低"
    }
  ]
}"""
        for m in ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-2.5-flash', 'gemini-1.5-pro']:
            try:
                resp = client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.2
                    )
                )
                if resp and resp.text:
                    parsed = json.loads(resp.text)
                    data_cache.record_api_call(module_name=f"名師前瞻 ({guru_name})", model_name=m)
                    return parsed
            except Exception as em:
                logger.warning(f'Model {m} failed: {em}')
                continue
        return None
    except Exception as e:
        logger.error(f'Gemini guru analysis failed: {e}')
        return None

def analyze_forum_sentiment_with_gemini(topics_list, custom_key=None):
    api_key = get_api_key(custom_key)
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        summaries = []
        for t in topics_list[:12]:
            stks = ', '.join(t.get('stocks', []))
            txt = t.get('text', '')
            summaries.append(f'【標的：{stks}】：{txt}')
        context_text = '\n---\n'.join(summaries)

        prompt = f"""你是專精台股「數天至數月波段操盤（Swing Trading / Trend Following）」與主力散戶博弈的資深投資長。
以下是台灣股市同學會（CMoney）最新熱門社群發文：

{context_text}

短線操盤手核心痛點：最怕在「末升段」跟著散戶狂熱買在最高點被套牢數月；最渴望在「回測月線洗盤結束、散戶罵聲連連」時跟隨主力逢低低吸波段買點。
請嚴格過濾排除純存股ETF（如 0050, 0056, 00878 等），專注於具備波動度與產業題材的個股，進行【散戶情緒 vs 主力籌碼波段照妖鏡分析】，回傳 JSON 格式：
{{
  "overall_sentiment": "散戶狂熱誘多警戒 / 恐慌割肉主力洗盤 / 分歧震盪換手 / 主升段健康推進",
  "crowd_psychology": "散戶真實心理狀態與籌碼沈澱剖析（直指題材與族群，80字內）",
  "market_regime_impact": "對數天至數月波段操作者的進退指引（嚴禁心靈雞湯）",
  "hot_stocks_analysis": [
    {{
      "stock_name": "股票名稱",
      "symbol": "4碼股票代號（若為ETF則直接排除不收錄）",
      "retail_sentiment": "極端狂熱追價 / 恐慌停損停利 / 猶豫分歧 / 抱牢看好",
      "sentiment_score": 85,
      "swing_stage": "初升段(主力吸籌) / 主升段(軌道推進) / 末升段狂熱(誘多出貨) / 回測洗盤(測20MA支撐) / 破線修正段",
      "contrarian_verdict": "🔴 散戶接刀警戒(主力出貨) / 🟢 主力洗盤吃貨(波段安全買點) / 🔵 主力散戶共振(順勢抱波段) / ⚪ 破線觀望不接刀",
      "defense_support": "關鍵波段防守點（如 10MA、20MA月線或大量低點）",
      "swing_strategy": "數天至數月持股作戰指南：加碼時機、波段續抱條件、跌破撤退停損點（80字內明確執行規格）",
      "risk_level": "高 / 中 / 低"
    }}
  ]
}}"""
        for m in ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-2.5-flash', 'gemini-1.5-pro']:
            try:
                resp = client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.2
                    )
                )
                if resp and resp.text:
                    parsed = json.loads(resp.text)
                    data_cache.record_api_call(module_name="股市同學會輿情雷達", model_name=m)
                    return parsed
            except Exception as em:
                logger.warning(f'Forum model {m} failed: {em}')
                continue
        return None
    except Exception as e:
        logger.error(f'Gemini forum analysis failed: {e}')
        return None

_LAST_ERROR = ""

def get_last_error():
    global _LAST_ERROR
    return _LAST_ERROR

def test_api_connection(custom_key=None):
    """
    發送一次輕量測試請求至 Google Gemini API，驗證金鑰有效性並記錄 1 次用量
    """
    global _LAST_ERROR
    api_key = get_api_key(custom_key)
    if not api_key:
        _LAST_ERROR = "尚未設定 Gemini API Key，請先於側邊欄輸入並點擊 SAVE 儲存。"
        return False, _LAST_ERROR
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for m in ['gemini-2.0-flash', 'gemini-1.5-flash']:
            try:
                resp = client.models.generate_content(
                    model=m,
                    contents='請回覆一句簡短繁體中文台股祝福語（10字內）'
                )
                if resp and resp.text:
                    data_cache.record_api_call(module_name="API連線測試", model_name=m)
                    _LAST_ERROR = ""
                    return True, f"連線成功！Google Gemini ({m}) 回應：{resp.text.strip()}"
            except Exception as em:
                _LAST_ERROR = f"模型 {m} 呼叫失敗: {em}"
                continue
        return False, _LAST_ERROR or "Google 回傳空白內容"
    except Exception as e:
        _LAST_ERROR = f"API 呼叫異常: {e}"
        return False, _LAST_ERROR

def analyze_single_stock_with_gemini(symbol: str, name: str, news_list: list, tech_info: dict, custom_key=None):
    global _LAST_ERROR
    api_key = get_api_key(custom_key)
    if not api_key:
        _LAST_ERROR = "未找到有效的 GEMINI_API_KEY，請先至側邊欄填入並點擊 SAVE。"
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        
        # 安全組裝新聞（相容 dict 與純字串格式，徹底防範 AttributeError）
        formatted_news = []
        for n in news_list[:4]:
            if isinstance(n, dict):
                formatted_news.append(f"• {n.get('title', '')} ({n.get('publisher', '')})")
            elif isinstance(n, str):
                formatted_news.append(f"• {n.strip()}")
        news_text = "\n".join(formatted_news) or "近期無重大突發新聞"
        
        prompt = f"""
你是精通台股短線籌碼、老王均線與當沖/波段作戰的「資深首席操盤手」。
請針對以下個股進行【客觀操盤決策與覆盤報告】：

【個股標的】：{name} ({symbol})
【最新股價與漲跌】：現價 ${tech_info.get('close', 0)} ({tech_info.get('pct_change', 0):+}%)
【均線位階】：5MA=${tech_info.get('ma5', 0)} | 10MA=${tech_info.get('ma10', 0)} | 20MA生命線=${tech_info.get('ma20', 0)} | 60MA季線=${tech_info.get('ma60', 0)}
【量能與位階】：今日成交量={tech_info.get('vol', 0):,}張 (均量比 {tech_info.get('vol_ratio', 1.0)}倍)
【老王型態】：{tech_info.get('cloud_status', '均線整理')} ｜ 建議防守點：${tech_info.get('stop_loss', 0)}
【近期重大消息】：
{news_text}

請嚴格以繁體中文（台灣習慣用語）進行專業操盤診斷，並【回傳標準 JSON 格式】：
{{
  "verdict_signal": "積極做多 / 買黑不買紅逢低接 / 觀望蓄勢 / 破線減碼 / 嚴格停損清倉",
  "trader_notes": "操盤手白話核心覆盤（約80~120字，直指目前多空主戰場、籌碼與量價關鍵，告訴散戶明天開盤怎麼應對）",
  "entry_condition": "建議進場點或確認訊號（例如：回測5MA有守、帶量突破某價位）",
  "stop_loss_point": "關鍵停損防守位置（結合20MA或爆量K低點）",
  "target_point": "短線波段停利目標價",
  "risk_warning": "最大潛在風險警示（例如：短線乖離過大、主力出貨、大盤風向偏空）"
}}
"""
        for m in ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']:
            try:
                resp = client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        temperature=0.2
                    )
                )
                if resp and resp.text:
                    parsed = json.loads(resp.text)
                    from datetime import datetime, timezone, timedelta
                    now_tw = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
                    parsed['analyzed_at'] = now_tw
                    parsed['posture'] = parsed.get('verdict_signal', '波段關注')
                    parsed['stop_loss_plan'] = parsed.get('stop_loss_point', str(tech_info.get('stop_loss', '')))
                    parsed['target_plan'] = parsed.get('target_point', str(tech_info.get('target1', '')))
                    parsed['score'] = 75 if any(x in parsed['posture'] for x in ['多', '買', '強', '低接']) else (45 if any(x in parsed['posture'] for x in ['空', '賣', '損', '減碼']) else 60)
                    parsed['catalyst'] = parsed.get('entry_condition', '短線量價型態確立')
                    data_cache.record_api_call(module_name=f"個股診斷 ({name})", model_name=m)
                    _LAST_ERROR = ""
                    return parsed
            except Exception as em:
                _LAST_ERROR = f"模型 {m} 錯誤: {em}"
                logger.warning(f'Stock diagnosis model {m} failed: {em}')
                continue
        return None
    except Exception as e:
        _LAST_ERROR = f"執行異常: {e}"
        logger.error(f'Gemini stock diagnosis error: {e}')
        return None

