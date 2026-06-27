import requests
import feedparser
import time
import hashlib
import os

# ===== 환경변수 =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ===== RSS 설정 =====
GLOBAL_FEEDS = [
    "https://news.google.com/rss/search?q=coal+phase-out&hl=en-US&gl=US&ceid=US:en",
    "https://www.reuters.com/business/energy/rss"
]

KOREA_FEEDS = [
    "https://news.google.com/rss/search?q=한전+부채&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=국민연금+기후&hl=ko&gl=KR&ceid=KR:ko"
]

# ✅ ✅ 핵심: 요청하신 키워드
KEYWORDS = [
    "한전 부채",
    "국민연금 기후",
    "석탄발전",
    "탈석탄"
]

CHECK_INTERVAL = 600  # 10분

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


# ===== 중복 방지 =====
def hash_title(title):
    return hashlib.md5(title.encode()).hexdigest()


# ===== 키워드 필터 =====
def contains_keyword(text):
    text = text.replace(" ", "")
    keywords_processed = [k.replace(" ", "") for k in KEYWORDS]
    return any(k in text for k in keywords_processed)


# ===== AI 요약 =====
def summarize(text):

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    prompt = f"""
다음 뉴스 제목을 2줄로 요약하세요.
정책/금융 영향 중심으로 핵심만:

{text}
"""

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    res = requests.post(url, headers=headers, json=data)
    result = res.json()

    return result["choices"][0]["message"]["content"]


# ===== 뉴스 처리 =====
def process_feed(feed_url, region):

    feed = feedparser.parse(feed_url)

    for entry in feed.entries[:5]:
        title = entry.title
        link = entry.link

        # 키워드 필터
        if not contains_keyword(title):
            continue

        key = hash_title(title)
        if key in posted:
            continue

        posted.add(key)

        # AI 요약
        try:
            summary = summarize(title)
        except:
            summary = "(요약 실패)"

        label = "🇰🇷 Korea" if region == "KR" else "🌏 Global"

        message = f"""
{label} <b>Climate Finance News</b>

<b>{title}</b>

{summary}

👉 {link}
"""

        send_telegram(message)
        print("Sent:", title)


# ===== 메인 루프 =====
while True:
    try:
        for f in GLOBAL_FEEDS:
            process_feed(f, "GLOBAL")

        for f in KOREA_FEEDS:
            process_feed(f, "KR")

    except Exception as e:
        print("Error:", e)

    time.sleep(CHECK_INTERVAL)
