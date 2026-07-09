"""
Saarangsha (ସାରାଂଶ) — news fetch + translate pipeline
------------------------------------------------------
Pulls public RSS headlines + teaser text from WSJ, NYT, and FT
(free, publicly published feeds — NOT the paywalled full articles),
translates them into Odia using Sarvam AI's translation API,
and writes the result to data.json for the frontend to read.

Setup:
    pip install feedparser sarvamai
    export SARVAM_API_KEY="your_key_here"   # get one at https://dashboard.sarvam.ai

Run:
    python fetch_news.py
"""

import os
import json
import time
import hashlib
import feedparser
from sarvamai import SarvamAI

# ---------------------------------------------------------------------------
# 1. CONFIG
# ---------------------------------------------------------------------------

# Public RSS feeds. Verify these still resolve — publishers occasionally
# restructure feed URLs. Each entry only gives us a headline + short teaser,
# never the full paywalled article.
RSS_FEEDS = {
    "NYT": [
        ("World",   "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
        ("Business","https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"),
    ],
    "WSJ": [
        ("World",   "https://feeds.a.dj.com/rss/RSSWorldNews.xml"),
        ("Markets", "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ],
    "FT": [
        ("World",   "https://www.ft.com/world?format=rss"),
    ],
}

ENTRIES_PER_FEED = 3          # how many stories to pull per feed
TARGET_LANG = "od-IN"         # Odia
SOURCE_LANG = "en-IN"
TRANSLATE_MODEL = "mayura:v1" # good general-purpose model; supports Odia natively
CACHE_FILE = "translation_cache.json"
OUTPUT_FILE = "data.json"

# ---------------------------------------------------------------------------
# 2. CACHE (avoid re-translating + re-paying for the same story every run)
# ---------------------------------------------------------------------------

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def cache_key(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------------------
# 3. TRANSLATE
# ---------------------------------------------------------------------------

def translate(client, text, cache):
    if not text:
        return ""
    key = cache_key(text)
    if key in cache:
        return cache[key]

    # mayura:v1 caps input at 1000 chars per call
    text = text[:1000]
    result = client.text.translate(
        input=text,
        source_language_code=SOURCE_LANG,
        target_language_code=TARGET_LANG,
        model=TRANSLATE_MODEL,
    )
    translated = result.translated_text
    cache[key] = translated
    return translated

# ---------------------------------------------------------------------------
# 4. FETCH + BUILD
# ---------------------------------------------------------------------------

def strip_html(raw):
    import re
    return re.sub("<[^<]+?>", "", raw or "").strip()

def estimate_read_time_odia(text):
    # rough: Odia readers ~ 150 words/min for unfamiliar-script reading
    words = max(len(text.split()), 1)
    minutes = max(1, round(words / 40))
    return minutes

def build_feed():
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        raise SystemExit(
            "Missing SARVAM_API_KEY. Get one at https://dashboard.sarvam.ai "
            "and run: export SARVAM_API_KEY=your_key_here"
        )
    client = SarvamAI(api_subscription_key=api_key)
    cache = load_cache()

    items = []
    for source, feeds in RSS_FEEDS.items():
        for category, url in feeds:
            print(f"Fetching {source} / {category} ...")
            try:
                parsed = feedparser.parse(url)
            except Exception as e:
                print(f"  ! failed to fetch {url}: {e}")
                continue

            if parsed.bozo and not parsed.entries:
                print(f"  ! no entries parsed from {url} (feed may have changed)")
                continue

            for entry in parsed.entries[:ENTRIES_PER_FEED]:
                title_en = strip_html(entry.get("title", ""))
                summary_en = strip_html(entry.get("summary", entry.get("description", "")))
                link = entry.get("link", "")
                published = entry.get("published", "")

                if not title_en:
                    continue

                print(f"  translating: {title_en[:60]}...")
                title_od = translate(client, title_en, cache)
                summary_od = translate(client, summary_en, cache) if summary_en else ""
                time.sleep(0.3)  # be gentle on the API

                items.append({
                    "source": source,
                    "category": category,
                    "title_en": title_en,
                    "summary_en": summary_en,
                    "title_od": title_od,
                    "summary_od": summary_od,
                    "link": link,
                    "published": published,
                    "read_min": estimate_read_time_odia(summary_od or title_od),
                })

    save_cache(cache)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"generated_at": time.strftime("%Y-%m-%d %H:%M"), "items": items}, f,
                   ensure_ascii=False, indent=2)

    print(f"\nDone. Wrote {len(items)} stories to {OUTPUT_FILE}")

if __name__ == "__main__":
    build_feed()
