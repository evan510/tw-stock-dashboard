import requests
from bs4 import BeautifulSoup
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
__all__ = [
    'fetch_cmoney_popular_topics',
    'fetch_cmoney_ranking_symbols',
    'is_etf_or_index',
    'evaluate_swing_contrarian_signal'
]

# 排除存股 ETF、期貨與大盤標籤，專注動能個股
IGNORE_SYMBOLS = {
    'rank', 'change-up', 'institutional-investor-buy', 'lend-increase', 'revenue-growth-mom',
    'TWA00', 'TWC00', '加權指數', '櫃買指數', '0050', '0056', '00878', '00919', '00929',
    '00940', '00713', '006208', '00939', '00935', '00881', '00981A', '00998A', '00983A',
    '00401A', '00981D', '00999A'
}

def is_etf_or_index(symbol: str) -> bool:
    s = str(symbol).strip()
    if s.startswith('00') or s.startswith('01') or len(s) > 4 or not s.isdigit():
        return True
    return s in IGNORE_SYMBOLS

def fetch_cmoney_popular_topics():
    """
    爬取股市同學會熱門文章，過濾純存股ETF話題，聚焦具題材爆發力之個股討論
    """
    url = 'https://www.cmoney.tw/forum/popular'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.encoding = 'utf-8'
        if resp.status_code != 200:
            logger.warning(f'CMoney HTTP Error: {resp.status_code}')
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        articles = soup.find_all('article')
        
        items = []
        for art in articles:
            stock_tags = []
            for link in art.find_all('a', href=re.compile(r'/forum/stock/\w+')):
                t = link.text.strip()
                if t and t not in stock_tags and not t.startswith('http') and len(t) <= 15:
                    if not is_etf_or_index(t) and t not in ['大盤', '美股', '總經']:
                        stock_tags.append(t)
            
            clean_text = ' '.join(art.text.split())
            # 排除純心靈雞湯但無實質標的之文章
            if len(clean_text) > 30:
                items.append({
                    'stocks': stock_tags,
                    'text': clean_text[:400],
                    'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M')
                })
        return items
    except Exception as e:
        logger.error(f'fetch cmoney popular topics error: {e}')
        return []

def fetch_cmoney_ranking_symbols():
    """
    取得股市同學會討論排行榜前 15 名之動能個股（過濾存股型ETF）
    """
    url = 'https://www.cmoney.tw/forum/stock/rank'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.find_all('a', href=True)
        symbols = []
        
        for l in links:
            href = l['href']
            if '/forum/stock/' in href:
                sym = href.split('/')[-1]
                if sym and sym not in IGNORE_SYMBOLS and not is_etf_or_index(sym) and sym not in symbols:
                    symbols.append(sym)
        return symbols[:15]
    except Exception as e:
        logger.error(f'fetch ranking error: {e}')
        return []

def evaluate_swing_contrarian_signal(symbol: str, name: str, sentiment_score: int):
    """
    【散戶 vs 主力波段照妖鏡演算法】
    整合 10MA、20MA 生命線與籌碼位階，診斷散戶情緒是「主力出貨警報」還是「洗盤低吸買點」
    """
    try:
        import data_engine
        df = data_engine.get_stock_history(symbol, period='4mo')
        if df is None or len(df) < 20:
            return {
                "close": "N/A", "ma10": "N/A", "ma20": "N/A",
                "swing_stage": "多空觀察整理",
                "contrarian_verdict": "均線位階確認中",
                "defense_support": "依前波低點防守"
            }
        
        close = round(float(df['Close'].iloc[-1]), 2)
        ma10 = round(float(df['Close'].tail(10).mean()), 2)
        ma20 = round(float(df['Close'].tail(20).mean()), 2)
        ma60 = round(float(df['Close'].tail(60).mean()), 2) if len(df) >= 60 else ma20
        
        # 散戶狂熱指數 (50-100) vs 技術面位階
        # 情境 1: 散戶極端狂熱 (>75分) 但高檔離月線過遠或破 10MA -> 散戶接刀 / 主力誘多出貨
        if sentiment_score >= 75:
            if close < ma10:
                swing_stage = "末升段狂熱警示 (籌碼渙散)"
                contrarian_verdict = "🔴 散戶接刀警戒 (主力逢高調節)"
                defense = f"${ma20} (20MA月線)"
            elif close > ma20 * 1.15:
                swing_stage = "噴出延伸段 (正乖離過大)"
                contrarian_verdict = "⚠️ 慎防假突破回馬槍 (嚴禁追價)"
                defense = f"${ma10} (10MA短線防守)"
            else:
                swing_stage = "主升段波段推進"
                contrarian_verdict = "🔵 主力散戶共振 (多頭順風車)"
                defense = f"${ma20} (波段生命線)"
                
        # 情境 2: 散戶悲觀恐慌 (<50分)，但回測 20MA 月線有撐 -> 主力洗盤吃貨買點
        elif sentiment_score <= 50:
            if close >= ma20:
                swing_stage = "回測洗盤整理 (支撐確立)"
                contrarian_verdict = "🟢 主力洗盤吃貨 (波段低吸好球帶)"
                defense = f"${ma20} (20MA跌破即停損)"
            else:
                swing_stage = "弱勢修正空方段"
                contrarian_verdict = "⚪ 破線觀望 (不盲目抄底)"
                defense = f"${ma60} (季線最後防線)"
                
        # 情境 3: 散戶中性觀望 (50-74分)
        else:
            if close > ma20 and ma10 >= ma20:
                swing_stage = "波段初升/多頭排列"
                contrarian_verdict = "🟢 籌碼沉澱乾淨 (波段蓄勢待發)"
                defense = f"${ma20} (20MA月線)"
            else:
                swing_stage = "區間箱型震盪"
                contrarian_verdict = "🟡 多空平衡觀望"
                defense = f"${ma20} (整理區下緣)"

        return {
            "close": close,
            "ma10": ma10,
            "ma20": ma20,
            "swing_stage": swing_stage,
            "contrarian_verdict": contrarian_verdict,
            "defense_support": defense
        }
    except Exception as e:
        logger.error(f"evaluate contrarian signal error: {e}")
        return {
            "close": "N/A", "ma10": "N/A", "ma20": "N/A",
            "swing_stage": "整理段",
            "contrarian_verdict": "觀望",
            "defense_support": "依波段紀律防守"
        }

