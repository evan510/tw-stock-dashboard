import os
import json
import logging
from dotenv import load_dotenv
import data_cache

load_dotenv()
logger = logging.getLogger(__name__)

def get_api_key(custom_key=None):
    if custom_key and str(custom_key).strip():
        return str(custom_key).strip()
    return os.environ.get('GEMINI_API_KEY', '').strip()

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
        for m in ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']:
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

        prompt = f"""你是專精台股籌碼與散戶心理學的操盤分析師。
以下是台灣股市同學會（CMoney）的熱門發文：

{context_text}

請進行【散戶情緒溫度計與買賣篩選分析】，並回傳JSON格式：
{
  "overall_sentiment": "極度熱絡 / 追高恐慌 / 分歧震痪 / 逢低抄底 / 悲觀停�%8損",
  "crowd_psychology": "散戶當前心理狀態總結（約80字）",
  "market_regime_impact": "對短線大盤的警訊或契機",
  "hot_stocks_analysis": [
    {
      "stock_name": "股票名稱",
      "symbol": "股票代號（4碼數字，無明確則留空）",
      "retail_sentiment": "一面倒看多 / 偏空唱衰 / 意見分歧",
      "sentiment_score": 80,
      "ai_trading_advice": "可逢低承接 / 嚄禁追高 / 跌破停�%8損觀望 / 波段續抱",
      "key_reason": "分析原因（60字內）",
      "risk_level": "高 / 中 / 低"
    }
  ]
}"""
        for m in ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']:
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

def analyze_single_stock_with_gemini(symbol: str, name: str, news_list: list, tech_info: dict, custom_key=None):
    api_key = get_api_key(custom_key)
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        
        # 組裝新聞與技術面上下文
        news_text = "\n".join([f"• {n.get('title', '')} ({n.get('publisher', '')})" for n in news_list[:4]]) or "近期無重大突發新聞"
        
        prompt = f"""
你是一位精通台股短線籌碼、老王均線與當沖/波段作戰的「資深首席操盤手」。
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
        for m in ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']:
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
                    data_cache.record_api_call(module_name=f"個股診斷 ({name})", model_name=m)
                    return parsed
            except Exception as em:
                logger.warning(f'Stock diagnosis model {m} failed: {em}')
                continue
        return None
    except Exception as e:
        logger.error(f'Gemini stock diagnosis error: {e}')
        return None

