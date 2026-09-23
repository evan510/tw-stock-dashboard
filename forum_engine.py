import requests
from bs4 import BeautifulSoup
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ─────────────────────────────────────────────
# CMoney 同學會
# ─────────────────────────────────────────────

def fetch_cmoney_popular_topics():
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
                    stock_tags.append(t)
            
            clean_text = ' '.join(art.text.split())
            if len(clean_text) > 30:
                items.append({
                    'stocks': stock_tags,
                    'text': clean_text[:350],
                    'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'source': 'CMoney'
                })
        return items
    except Exception as e:
        logger.error(f'fetch cmoney popular topics error: {e}')
        return []

def fetch_cmoney_ranking_symbols():
    url = 'https://www.cmoney.tw/forum/stock/rank'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = soup.find_all('a', href=True)
        symbols = []
        ignore = {'rank', 'change-up', 'institutional-investor-buy', 'lend-increase', 'revenue-growth-mom', 'TWA00', 'TWC00'}
        for l in links:
            href = l['href']
            if '/forum/stock/' in href:
                sym = href.split('/')[-1]
                if sym and sym not in ignore and sym not in symbols:
                    symbols.append(sym)
        return symbols[:15]
    except Exception as e:
        logger.error(f'fetch ranking error: {e}')
        return []

# ─────────────────────────────────────────────
# PTT Stock 版熱門文章
# ─────────────────────────────────────────────

def fetch_ptt_stock_hot(max_articles=15):
    """
    爬取 PTT Stock 版熱門文章（推文數 >= 10）
    回傳格式：[{title, url, push_count, author, date, source}]
    """
    url = 'https://www.ptt.cc/bbs/Stock/index.html'
    # PTT 需要帶 over18 cookie 繞過年齡確認
    cookies = {'over18': '1'}
    try:
        resp = requests.get(url, headers=HEADERS, cookies=cookies, timeout=12)
        resp.encoding = 'utf-8'
        if resp.status_code != 200:
            logger.warning(f'PTT HTTP Error: {resp.status_code}')
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        divs = soup.find_all('div', class_='r-ent')
        
        articles = []
        for div in divs:
            try:
                # 推文數
                push_tag = div.find('div', class_='nrec')
                push_text = push_tag.text.strip() if push_tag else '0'
                # 爆文 = '爆', 負推文 = 'X'
                if push_text == '爆':
                    push_count = 100
                elif push_text.startswith('X'):
                    push_count = -int(push_text[1:]) if push_text[1:].isdigit() else -1
                else:
                    push_count = int(push_text) if push_text.isdigit() else 0

                # 只取推文數 >= 10 的文章
                if push_count < 10:
                    continue

                title_tag = div.find('div', class_='title')
                if not title_tag or not title_tag.a:
                    continue
                title = title_tag.a.text.strip()
                link = 'https://www.ptt.cc' + title_tag.a['href']

                # 作者
                author_tag = div.find('div', class_='author')
                author = author_tag.text.strip() if author_tag else ''

                # 日期
                date_tag = div.find('div', class_='date')
                date = date_tag.text.strip() if date_tag else ''

                articles.append({
                    'title': title,
                    'url': link,
                    'push_count': push_count if push_count < 100 else '爆',
                    'author': author,
                    'date': date,
                    'source': 'PTT Stock',
                    'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M')
                })
            except Exception:
                continue

        return articles[:max_articles]
    except Exception as e:
        logger.error(f'fetch PTT stock error: {e}')
        return []


def fetch_ptt_stock_hot_text_summary(max_articles=15):
    """
    取得 PTT Stock 熱門文章並整理為純文字摘要（供 Gemini AI 分析）
    """
    articles = fetch_ptt_stock_hot(max_articles=max_articles)
    if not articles:
        return []
    
    result = []
    for a in articles:
        push_str = str(a['push_count']) if isinstance(a['push_count'], int) else a['push_count']
        result.append({
            'stocks': [],  # PTT 標題較難抽股票代號，交給 AI
            'text': f"[推{push_str}] {a['title']}",
            'source': 'PTT Stock',
            'url': a.get('url', ''),
            'scraped_at': a.get('scraped_at', '')
        })
    return result


def fetch_all_forum_topics(include_ptt=True):
    """
    整合 CMoney + PTT 論壇熱門話題（統一格式）
    """
    topics = fetch_cmoney_popular_topics()
    if include_ptt:
        ptt_topics = fetch_ptt_stock_hot_text_summary(max_articles=10)
        topics = topics + ptt_topics
    return topics
