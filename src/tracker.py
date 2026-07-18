#!/usr/bin/env python3
"""
UAE FS Regulatory Tracker - polling job (run every 2 hours by GitHub Actions).
"""

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "sources.yaml"
STATE_FILE = ROOT / "data" / "state.json"
ITEMS_FILE = ROOT / "data" / "items.json"
HTML_FILE = ROOT / "data" / "latest.html"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36 UAE-FS-RegTracker/1.0"
    ),
    "Accept-Language": "en",
}

MIN_TITLE_LEN = 25
MAX_ITEMS_PER_SOURCE = 40


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().rstrip("/").encode()).hexdigest()[:16]


def clean_title(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def fetch(url: str):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.text
            print(f"  [warn] {url} -> HTTP {r.status_code}")
        except requests.RequestException as e:
            print(f"  [warn] {url} attempt {attempt+1}: {e}")
        time.sleep(2 * (attempt + 1))
    return None


def harvest_links(html, base_url, patterns, exclude=None):
    soup = BeautifulSoup(html, "html.parser")
    base_host = urlparse(base_url).netloc
    seen, items = set(), []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"].strip())
        parsed = urlparse(href)
        if parsed.netloc != base_host:
            continue
        low = href.lower()
        if not any(p.lower() in low for p in patterns):
            continue
        if exclude and any(x.lower() in low for x in exclude):
            continue
        if href.rstrip("/") == base_url.rstrip("/"):
            continue
        title = clean_title(a.get_text(" "))
        if len(title) < MIN_TITLE_LEN:
            parent = a.find_parent(["article", "li", "div"])
            if parent:
                h = parent.find(["h1", "h2", "h3", "h4"])
                if h:
                    title = clean_title(h.get_text(" "))
        if len(title) < MIN_TITLE_LEN:
            continue
        if href in seen:
            continue
        seen.add(href)
        items.append({"title": title[:300], "url": href})
        if len(items) >= MAX_ITEMS_PER_SOURCE:
            break
    return items


def keyword_relevant(title, keywords):
    t = title.lower()
    return any(k.lower() in t for k in keywords)


def classify_with_claude(items):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not items:
        return None
    try:
        payload_items = [
            {"id": i, "title": it["title"], "regulator": it["regulator"]}
            for i, it in enumerate(items)
        ]
        prompt = (
            "You are triaging headlines for a UAE financial services regulatory "
            "lawyer covering ADGM (FSRA), DIFC (DFSA) and onshore UAE (CBUAE, "
            "SCA, VARA). For each item decide if a practising FS reg lawyer "
            "must know it (new rules, consultations, enforcement, licensing "
            "policy, AML/sanctions, virtual assets, prudential/conduct "
            "changes, key federal laws). Ignore pure PR (awards, event promos, "
            "graduate programmes, MoU photo-ops with no regulatory substance).\n\n"
            "Respond ONLY with a JSON array, one object per item: "
            '{"id": <int>, "relevant": true|false, "priority": "high"|"medium"|"low", '
            '"why": "<max 25 words, practical significance>"}\n\n'
            f"Items:\n{json.dumps(payload_items, ensure_ascii=False)}"
        )
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=120,
        )
        r.raise_for_status()
        text = "".join(
            b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text"
        )
        text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
        return {row["id"]: row for row in json.loads(text)}
    except Exception as e:
        print(f"  [warn] Claude classification skipped: {e}")
        return None


def render_html(items):
    items = sorted(items, key=lambda x: x["first_seen"], reverse=True)[:200]
    groups = {"ADGM": [], "DIFC": [], "ONSHORE": []}
    for it in items:
        groups.setdefault(it["jurisdiction"], []).append(it)
    now = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    parts = [
        "<!doctype html><meta charset='utf-8'>",
        "<title>UAE FS Regulatory Tracker</title>",
        "<style>body{font-family:Georgia,serif;max-width:860px;margin:2rem auto;"
        "padding:0 1rem;color:#1a1a2e}h1{font-size:1.5rem}h2{border-bottom:2px solid #b08d2f;"
        "padding-bottom:4px;margin-top:2rem}li{margin:.6rem 0;line-height:1.45}"
        ".meta{color:#666;font-size:.85rem}.hi{color:#8b1a1a;font-weight:bold}</style>",
        f"<h1>UAE Financial Services Regulatory Tracker</h1>"
        f"<p class='meta'>Last polled: {now}. Showing latest 200 tracked items.</p>",
    ]
    labels = {"ADGM": "ADGM (FSRA)", "DIFC": "DIFC (DFSA)", "ONSHORE": "Onshore UAE (CBUAE / SCA / VARA)"}
    for j in ("ADGM", "DIFC", "ONSHORE"):
        parts.append(f"<h2>{labels[j]}</h2><ul>")
        for it in groups.get(j, []):
            pr = " <span class='hi'>[HIGH]</span>" if it.get("priority") == "high" else ""
            why = f"<br><span class='meta'>{it['why']}</span>" if it.get("why") else ""
            parts.append(
                f"<li><a href='{it['url']}'>{it['title']}</a>{pr}"
                f"<br><span class='meta'>{it['regulator']} · first seen "
                f"{it['first_seen'][:10]}</span>{why}</li>"
            )
        parts.append("</ul>")
    HTML_FILE.write_text("".join(parts), encoding="utf-8")


def main():
    cfg = load_yaml(CONFIG)
    keywords = cfg.get("keywords", [])
    state = load_json(STATE_FILE, {"seen": {}})
    items = load_json(ITEMS_FILE, [])
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    candidates = []
    for src in cfg["sources"]:
        print(f"Polling: {src['name']} ({src['url']})")
        html = fetch(src["url"])
        if not html:
            continue
        found = harvest_links(
            html, src["url"], src["link_patterns"], src.get("exclude_patterns")
        )
        fresh = 0
        for it in found:
            h = url_hash(it["url"])
            if h in state["seen"]:
                continue
            is_rule_source = any(
                w in src["name"].lower() for w in ("consultation", "rulebook")
            )
            if not is_rule_source and not keyword_relevant(it["title"], keywords):
                state["seen"][h] = now_iso
                continue
            candidates.append(
                {
                    **it,
                    "hash": h,
                    "source": src["name"],
                    "jurisdiction": src["jurisdiction"],
                    "regulator": src["regulator"],
                    "first_seen": now_iso,
                }
            )
            fresh += 1
        print(f"  {len(found)} links harvested, {fresh} new candidates")

    verdicts = classify_with_claude(candidates)
    accepted = []
    for i, it in enumerate(candidates):
        state["seen"][it["hash"]] = now_iso
        v = verdicts.get(i) if verdicts else None
        if v is not None:
            if not v.get("relevant", True):
                continue
            it["priority"] = v.get("priority", "medium")
            it["why"] = v.get("why", "")
        accepted.append(it)

    if accepted:
        items.extend(accepted)
        print(f"Added {len(accepted)} new item(s).")
    else:
        print("No new relevant items this cycle.")

    items = items[-3000:]
    save_json(STATE_FILE, state)
    save_json(ITEMS_FILE, items)
    render_html(items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
