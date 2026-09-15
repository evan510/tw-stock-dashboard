import requests
from bs4 import BeautifulSoup
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

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
                    'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M')
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
