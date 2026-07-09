# ସାରାଂଶ (Saarangsha) — real pipeline

A small working app: pulls public headlines + teaser text from WSJ, NYT, and FT,
translates them into Odia using **Sarvam AI**, and shows them in a mobile-friendly
web page.

## Why RSS, not full articles?

WSJ and FT are paywalled — there's no free, legal way to pull their full article
text. What every major paper *does* publish freely is an RSS feed with the
**headline + a short public teaser** (the same snippet you'd see on Google News
or Twitter). That's what this pipeline translates. It's legal, free, and it's
already the "short read" format you asked for — no separate summarization step
needed for now.

If you later want deeper summaries of full articles, that requires a licensing
deal with each publisher (e.g. an NYT API partnership) — a bigger step, worth
doing once you've validated the concept.

## 1. Get a Sarvam API key

Sign up at https://dashboard.sarvam.ai — free tier is enough to start.

```bash
export SARVAM_API_KEY="your_key_here"
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Fetch + translate

```bash
python fetch_news.py
```

This writes `data.json` with the latest stories translated into Odia, and caches
translations in `translation_cache.json` so re-runs don't re-pay for the same story.

## 4. View the app

Just open `index.html` in a browser — or serve it locally:

```bash
python -m http.server 8000
```

Then visit http://localhost:8000

## Notes / things to check before relying on this

- **RSS URLs drift.** The feed URLs in `fetch_news.py` (`RSS_FEEDS`) are the
  standard public feeds as of writing — if a fetch returns 0 entries, check
  whether the publisher moved the feed and update the URL.
- **`mayura:v1`** caps input at 1000 characters per call, which is fine for
  headlines/teasers but keep in mind if you swap in longer text later.
- **Rate/cost**: each headline + teaser is 1–2 API calls. With ~18 stories per
  run (3 feeds × 2 sources × 3 entries) that's manageable on the free tier;
  scale up gradually.
- This is a static-file prototype (no server, no database). For a real product
  you'd want: a scheduled job (cron) running `fetch_news.py` every N hours,
  and the frontend served from wherever you host static files.
