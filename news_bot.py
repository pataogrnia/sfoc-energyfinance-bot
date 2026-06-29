import requests
import feedparser
import time
import hashlib
import os

# ===== 환경변수 (Railway에서 설정) =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# ===== RSS 설정 =====
GLOBAL_FEEDS = [
    "https://news.google.com/rss/search?q=coal+phase-out&hl=en-US&gl=US&ceid=US:en",
    "https://www.reuters.com/business/energy/rss"
]

KOREA_FEEDS = [
    "https://news.google.com/rss/search?q=한전+부채&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=국민연금+기후&hl=ko&gl=KR&ceid=KR:ko"
]

# ===== 키워드 (SFOC 맞춤) =====
KEYWORDS = [
    "한전 부채",
    "국민연금 기후",
    "석탄발전",
    "탈석탄"
]

CHECK_INTERVAL = 600  # 10분

# ===== 중복 방지 =====
posted = set()

# ===== 텔레그램 전송 =====
def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=data)

# ===== 키워드 필터 =====
def contains_keyword(text):
    text = text.replace(" ", "")
    keywords_processed = [k.replace(" ", "") for k in KEYWORDS]
    return any(k in text for k in keywords_processed)

# ===== 제목 해시 (중복 방지) =====
def hash_title(title):
    return hashlib.md5(title.encode()).hexdigest()

# ===== 뉴스 처리 =====
def process_feed(feed_url, region):

    feed = feedparser.parse(feed_url)

    for entry in feed.entries[:5]:
        title = entry.title
        link = entry.link

        # 키워드 필터
        if not contains_keyword(title):
            continue

        # 중복 방지
        key = hash_title(title)
        if key in posted:
            continue

        posted.add(key)

        # 지역 표시
