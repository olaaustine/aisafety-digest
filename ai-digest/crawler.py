#!/usr/bin/env python3
"""
AI Digest — daily crawler for AI/alignment content.
Scrapes 6 sources and generates a static index.html.
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from pathlib import Path
import json
import re

SOURCES = [
    {
        "name": "LessWrong",
        "url": "https://www.lesswrong.com",
        "feed": "https://www.lesswrong.com/feed.xml",
        "type": "rss",
    },
    {
        "name": "Alignment Forum",
        "url": "https://www.alignmentforum.org",
        "feed": "https://www.alignmentforum.org/feed.xml",
        "type": "rss",
    },
    {
        "name": "BlueDot Blog",
        "url": "https://blog.bluedot.org",
        "feed": "https://blog.bluedot.org/rss/",
        "type": "rss",
    },
    {
        "name": "Forethought",
        "url": "https://forethought.org",
        "feed": "https://forethought.org/blog/",
        "type": "scrape",
        "selector": "article a, .post a, .blog-post a, h2 a, h3 a",
    },
    {
        "name": "arXiv AI",
        "url": "https://arxiv.org",
        "feed": "https://arxiv.org/rss/cs.AI",
        "type": "rss",
    },
    {
        "name": "Anthropic News",
        "url": "https://www.anthropic.com/news",
        "feed": "https://www.anthropic.com/news",
        "type": "scrape",
        "selector": "a[href*='/news/']",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Digest-Bot/1.0)"
}

MAX_ITEMS = 10  # per source


def fetch_rss(source: dict) -> list[dict]:
    try:
        feed = feedparser.parse(source["feed"])
        items = []
        for entry in feed.entries[:MAX_ITEMS]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if title and link:
                items.append({"title": title, "url": link})
        return items
    except Exception as e:
        print(f"  [RSS error] {source['name']}: {e}")
        return []


def fetch_scrape(source: dict) -> list[dict]:
    try:
        resp = requests.get(source["feed"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        seen = set()
        items = []
        for a in soup.select(source["selector"]):
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if not title or not href or len(title) < 10:
                continue
            if not href.startswith("http"):
                href = source["url"].rstrip("/") + "/" + href.lstrip("/")
            if href in seen:
                continue
            seen.add(href)
            items.append({"title": title, "url": href})
            if len(items) >= MAX_ITEMS:
                break
        return items
    except Exception as e:
        print(f"  [Scrape error] {source['name']}: {e}")
        return []


def crawl_all() -> list[dict]:
    results = []
    for source in SOURCES:
        print(f"Crawling {source['name']}...")
        if source["type"] == "rss":
            articles = fetch_rss(source)
        else:
            articles = fetch_scrape(source)
        print(f"  → {len(articles)} articles")
        results.append({
            "name": source["name"],
            "url": source["url"],
            "articles": articles,
        })
    return results


def render_html(data: list[dict], date_str: str) -> str:
    source_blocks = ""
    for source in data:
        articles_html = ""
        if source["articles"]:
            for a in source["articles"]:
                title = a["title"].replace("<", "&lt;").replace(">", "&gt;")
                url = a["url"].replace('"', "%22")
                articles_html += f'<li><a href="{url}" target="_blank" rel="noopener">{title}</a></li>\n'
        else:
            articles_html = '<li class="empty">No articles fetched today.</li>'

        source_blocks += f"""
<div class="source-card">
  <div class="source-header">
    <a href="{source['url']}" target="_blank" rel="noopener" class="source-name">{source['name']}</a>
    <span class="source-count">{len(source['articles'])} articles</span>
  </div>
  <ul class="article-list">
    {articles_html}
  </ul>
</div>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI Digest — {date_str}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg: #0d0d0f; --bg2: #111114; --bg3: #16161a;
      --pink: #ff2d78; --pink-dim: #ff2d7822; --border: #1e1e26;
      --text: #e8e8f0; --muted: #6b6b80;
      --mono: 'JetBrains Mono', monospace;
      --sans: 'Inter', sans-serif;
    }}
    html {{ scroll-behavior: smooth; }}
    body {{ background: var(--bg); color: var(--text); font-family: var(--sans); line-height: 1.7; }}
    ::-webkit-scrollbar {{ width: 6px; }} ::-webkit-scrollbar-track {{ background: var(--bg); }} ::-webkit-scrollbar-thumb {{ background: var(--pink); border-radius: 3px; }}
    a {{ color: inherit; text-decoration: none; }}

    header {{
      background: rgba(13,13,15,.9); border-bottom: 1px solid var(--border);
      backdrop-filter: blur(12px); position: sticky; top: 0; z-index: 10;
      padding: 1rem 2rem; display: flex; align-items: center; justify-content: space-between;
    }}
    .logo {{ font-family: var(--mono); font-size: 1rem; font-weight: 600; }}
    .logo span {{ color: var(--pink); }}
    .date-badge {{
      font-family: var(--mono); font-size: .78rem; color: var(--muted);
      border: 1px solid var(--border); padding: .3rem .8rem; border-radius: 4px;
    }}

    .hero {{
      max-width: 900px; margin: 3rem auto 2rem; padding: 0 2rem; text-align: center;
    }}
    .hero h1 {{ font-size: clamp(1.6rem, 4vw, 2.4rem); font-weight: 600; margin-bottom: .5rem; }}
    .hero h1 span {{ color: var(--pink); }}
    .hero p {{ color: var(--muted); font-size: .93rem; font-family: var(--mono); }}

    .grid {{
      max-width: 900px; margin: 0 auto 4rem; padding: 0 2rem;
      display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 1.25rem;
    }}

    .source-card {{
      background: var(--bg2); border: 1px solid var(--border); border-radius: 8px;
      overflow: hidden; transition: border-color .2s;
    }}
    .source-card:hover {{ border-color: var(--pink); }}

    .source-header {{
      display: flex; align-items: center; justify-content: space-between;
      padding: .9rem 1.25rem; border-bottom: 1px solid var(--border);
      background: var(--bg3);
    }}
    .source-name {{
      font-family: var(--mono); font-size: .88rem; font-weight: 600; color: var(--pink);
    }}
    .source-name:hover {{ opacity: .8; }}
    .source-count {{
      font-family: var(--mono); font-size: .72rem; color: var(--muted);
      background: var(--bg); border: 1px solid var(--border);
      padding: .15rem .5rem; border-radius: 3px;
    }}

    .article-list {{ list-style: none; padding: .75rem 1.25rem 1rem; display: flex; flex-direction: column; gap: .5rem; }}
    .article-list li a {{
      font-size: .85rem; color: var(--muted);
      display: block; line-height: 1.5;
      transition: color .2s;
      border-left: 2px solid transparent; padding-left: .6rem;
    }}
    .article-list li a:hover {{ color: var(--text); border-left-color: var(--pink); }}
    .article-list li.empty {{ font-family: var(--mono); font-size: .78rem; color: var(--border); padding-left: .6rem; }}

    footer {{
      text-align: center; padding: 2rem; border-top: 1px solid var(--border);
      font-family: var(--mono); font-size: .75rem; color: var(--muted);
    }}
  </style>
</head>
<body>
  <header>
    <div class="logo"><span>&lt;</span>ai-digest<span>/&gt;</span></div>
    <div class="date-badge">{date_str}</div>
  </header>

  <div class="hero">
    <h1>Daily <span>AI</span> Digest</h1>
    <p>// curated from lesswrong · alignment forum · bluedot · forethought · arxiv · anthropic</p>
  </div>

  <div class="grid">
    {source_blocks}
  </div>

  <footer>Generated at {datetime.now(timezone.utc).strftime('%H:%M UTC')} · Built by Ola Austine</footer>
</body>
</html>"""


def main():
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    print(f"AI Digest — {date_str}")
    print("=" * 40)

    data = crawl_all()

    output = Path("index.html")
    output.write_text(render_html(data, date_str), encoding="utf-8")
    print(f"\nWrote {output}")

    # Save raw data as JSON for debugging
    Path("data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
