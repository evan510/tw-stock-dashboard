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
