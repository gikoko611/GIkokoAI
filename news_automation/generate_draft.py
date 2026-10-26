#!/usr/bin/env python3
"""Create one source-linked Burmese AI news draft as a GitHub Issue for human review."""
import json, os, sys, urllib.parse, urllib.request, urllib.error, xml.etree.ElementTree as ET
from datetime import datetime, timezone

REPO = os.getenv("GITHUB_REPOSITORY", "gikoko611/GIkokoAI")
TOKEN = os.getenv("GITHUB_TOKEN", "")
MODELGO_KEY = os.getenv("MODELGO_API_KEY", "")
MODELGO_BASE = os.getenv("MODELGO_BASE_URL", "https://api.modelgo.ai/v1").rstrip("/")
MODEL = os.getenv("NEWS_MODEL", "openai/gpt-oss-120b")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
SOURCES = [
    ("OpenAI News", "https://openai.com/news/rss.xml"),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
    ("Google AI Blog", "https://blog.google/technology/google-labs/rss/"),
    ("Anthropic News", "https://www.anthropic.com/news/rss.xml"),
]

def request(url, method="GET", payload=None, headers=None, timeout=25):
    data = json.dumps(payload).encode() if payload is not None else None
    h = {"User-Agent": "GIKOKO-AI-NewsBot/1.0", "Accept": "application/json, application/rss+xml, application/atom+xml, application/xml"}
    if data is not None: h["Content-Type"] = "application/json"
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if "json" in resp.headers.get("Content-Type", "").lower() else raw

def entries(feed_name, url):
    try:
        root = ET.fromstring(request(url))
    except Exception as exc:
        print(f"Feed unavailable: {feed_name}: {type(exc).__name__}")
        return []
    found = []
    for node in root.findall(".//item")[:12]:
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        desc = (node.findtext("description") or "").strip()
        date = (node.findtext("pubDate") or "").strip()
        if title and link.startswith("http"):
            found.append({"source": feed_name, "title": title, "url": link, "summary": desc[:1800], "date": date})
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    if not found:
        for node in root.findall(".//atom:entry", ns)[:12]:
            title = (node.findtext("atom:title", default="", namespaces=ns) or "").strip()
            linknode = node.find("atom:link", ns)
            link = linknode.attrib.get("href", "") if linknode is not None else ""
            desc = node.findtext("atom:summary", default="", namespaces=ns) or node.findtext("atom:content", default="", namespaces=ns)
            date = node.findtext("atom:updated", default="", namespaces=ns)
            if title and link.startswith("http"):
                found.append({"source": feed_name, "title": title, "url": link, "summary": desc[:1800], "date": date})
    return found

def issue_exists(url):
    q = urllib.parse.quote(f'repo:{REPO} "{url}" in:body')
    try:
        data = request(f"https://api.github.com/search/issues?q={q}", headers={"Accept":"application/vnd.github+json"})
        return data.get("total_count", 0) > 0
    except Exception:
        return False

def generate(story):
    prompt = (
        "You are the Burmese-language editor for G.I KO KO AI. Create a review-ready Facebook Page news draft from ONLY the source material below. "
        "Do not invent facts, quotes, dates, numbers, or implications. Clearly distinguish confirmed facts from uncertainty. "
        "If details are insufficient, say so and recommend checking the source. Write natural Burmese. Output: "
        "Headline; 2-4 short paragraphs; Why it matters (one sentence); source link; 3-5 relevant hashtags. "
        "Do not claim this is independently verified. Do not include markdown tables.\n\n"
        + json.dumps(story, ensure_ascii=False)
    )
    if MODELGO_KEY:
        data = request(MODELGO_BASE + "/chat/completions", "POST", {
            "model": MODEL, "messages":[{"role":"system","content":"Write accurate, cautious Burmese technology news."},{"role":"user","content":prompt}],
            "temperature":0.3, "max_tokens":900
        }, {"Authorization":"Bearer "+MODELGO_KEY}, timeout=60)
        return data["choices"][0]["message"]["content"].strip()
    if GEMINI_KEY:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        data = request(url, "POST", {"contents":[{"parts":[{"text":prompt}]}], "generationConfig":{"temperature":0.3,"maxOutputTokens":1200}},
                       {"x-goog-api-key":GEMINI_KEY}, timeout=60)
        return "".join(p.get("text","") for p in data["candidates"][0]["content"]["parts"]).strip()
    raise RuntimeError("Set MODELGO_API_KEY or GEMINI_API_KEY in GitHub Actions Secrets.")

def main():
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is missing.")
    all_stories = []
    for name, url in SOURCES:
        all_stories.extend(entries(name, url))
    if not all_stories:
        raise RuntimeError("No stories retrieved from configured RSS feeds.")
    # Prefer latest feed entries; source dates may have different formats, so preserve publisher order.
    story = next((s for s in all_stories if not issue_exists(s["url"])), None)
    if story is None:
        print("No new source stories; nothing to draft.")
        return
    draft = generate(story)
    title = "[NEWS REVIEW] " + story["title"][:180]
    body = (
        "## Status: WAITING FOR HUMAN REVIEW\n\n"
        "Review the source and draft before publishing. This issue does **not** publish automatically.\n\n"
        "### Source metadata\n"
        f"- Publisher/feed: {story['source']}\n- Published: {story['date'] or 'Not provided by feed'}\n- Original URL: {story['url']}\n\n"
        "### AI-generated Burmese draft\n\n" + draft + "\n\n"
        "### Reviewer checklist\n"
        "- [ ] Opened and checked the original source\n"
        "- [ ] Verified names, dates, numbers and claims\n"
        "- [ ] Edited Burmese wording and headline\n"
        "- [ ] Checked image/video rights and attribution\n"
        "- [ ] Approved for Facebook publishing\n\n"
        "_Generated at " + datetime.now(timezone.utc).isoformat() + ". Approval and publishing are separate steps._"
    )
    result = request(f"https://api.github.com/repos/{REPO}/issues", "POST",
                     {"title": title, "body": body},
                     {"Authorization":"Bearer "+TOKEN, "Accept":"application/vnd.github+json",
                      "X-GitHub-Api-Version":"2022-11-28"})
    print("Draft issue created:", result.get("html_url", "(URL unavailable)"))

if __name__ == "__main__":
    main()
