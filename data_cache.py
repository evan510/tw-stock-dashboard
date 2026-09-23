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
