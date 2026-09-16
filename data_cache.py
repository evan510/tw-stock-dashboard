import os
import json
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

GURU_CACHE_FILE = os.path.join(DATA_DIR, 'guru_history.json')
FORUM_CACHE_FILE = os.path.join(DATA_DIR, 'forum_sentiment.json')

def load_guru_history() -> dict:
    if not os.path.exists(GURU_CACHE_FILE):
        return {}
    try:
        with open(GURU_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f'load guru history error: {e}')
        return {}

def save_guru_analysis(video_id: str, analysis_data: dict):
    history = load_guru_history()
    now_str = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    history[video_id] = {
        **analysis_data,
        'cached_at': now_str
    }
    try:
        with open(GURU_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f'save guru history error: {e}')

def get_guru_analysis_from_cache(video_id: str):
    history = load_guru_history()
    return history.get(video_id)

def load_forum_sentiment() -> dict:
    if not os.path.exists(FORUM_CACHE_FILE):
        return {}
    try:
        with open(FORUM_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f'load forum cache error: {e}')
        return {}

def save_forum_sentiment(data: dict):
    try:
        now_str = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
        data['cached_at'] = now_str
        with open(FORUM_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f'save forum cache error: {e}')

def is_forum_cache_valid(max_age_hours=3) -> bool:
    data = load_forum_sentiment()
    if not data or 'cached_at' not in data:
        return False
    try:
        cached_dt = datetime.strptime(data['cached_at'], '%Y-%m-%d %H:%M:%S')
        now_dt = datetime.now()
        return (now_dt - cached_dt).total_seconds() < (max_age_hours * 3600)
    except Exception:
        return False

# ================= Gemini API 用量與快取節省統計 =================
USAGE_FILE = os.path.join(DATA_DIR, 'api_usage_stats.json')

def load_api_usage_stats() -> dict:
    today_str = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    default_stats = {
        "date": today_str,
        "today_calls": 0,
        "total_calls": 0,
        "cache_saved_calls": 0,
        "last_call_time": "無",
        "last_module": "無",
        "last_model": "無"
    }
    if not os.path.exists(USAGE_FILE):
        return default_stats
    try:
        with open(USAGE_FILE, 'r', encoding='utf-8') as f:
            stats = json.load(f)
            # 若跨日，重置今日呼叫計數
            if stats.get("date") != today_str:
                stats["date"] = today_str
                stats["today_calls"] = 0
            return stats
    except Exception:
        return default_stats

def record_api_call(module_name="Gemini", model_name="gemini-2.5-flash"):
    stats = load_api_usage_stats()
    now_str = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    stats["today_calls"] = stats.get("today_calls", 0) + 1
    stats["total_calls"] = stats.get("total_calls", 0) + 1
    stats["last_call_time"] = now_str
    stats["last_module"] = module_name
    stats["last_model"] = model_name
    try:
        with open(USAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"save usage error: {e}")

def record_cache_hit(module_name="Cache"):
    stats = load_api_usage_stats()
    stats["cache_saved_calls"] = stats.get("cache_saved_calls", 0) + 1
    try:
        with open(USAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"save cache hit error: {e}")

# ================= 個股 AI 深度診斷當日快取 (避免重複查詢消耗) =================
STOCK_AI_CACHE_FILE = os.path.join(DATA_DIR, 'stock_ai_cache.json')

def load_stock_ai_cache() -> dict:
    if not os.path.exists(STOCK_AI_CACHE_FILE):
        return {}
    try:
        with open(STOCK_AI_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def get_stock_ai_analysis_from_cache(symbol: str):
    cache = load_stock_ai_cache()
    today_str = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    item = cache.get(symbol)
    if item and item.get("date") == today_str:
        return item
    return None

def save_stock_ai_analysis(symbol: str, analysis_data: dict):
    cache = load_stock_ai_cache()
    today_str = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    now_str = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    cache[symbol] = {
        **analysis_data,
        "date": today_str,
        "cached_at": now_str
    }
    try:
        with open(STOCK_AI_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"save stock ai cache error: {e}")

