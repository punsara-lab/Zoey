import datetime
import os
import re

import requests

MAX_RESULTS = 5
MAX_SOURCE_CHARS = 1200


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = re.sub(r"[ \\t\\r\\n]+", " ", html)
    return html.strip()


def _fetch_text(url: str) -> str:
    try:
        resp = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (ZoeyResearchBot; +http://localhost)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        ct = (resp.headers.get("content-type") or "").lower()
        if "text/html" not in ct and "application/xhtml" not in ct and "text/plain" not in ct:
            return ""
        text = resp.text or ""
        return _strip_html(text)[:MAX_SOURCE_CHARS]
    except Exception:
        return ""


def research_topic(args: dict) -> str:
    topic = (args.get("topic") or "").strip()
    max_results = int(args.get("max_results") or MAX_RESULTS)
    if not topic:
        return "No topic given."

    try:
        from ddgs import DDGS
    except ImportError:
        return (
            "Research isn't available — the 'ddgs' package isn't installed. "
            "Run: pip install ddgs"
        )

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(topic, max_results=max(1, min(max_results, 10))))
    except Exception as e:
        return f"Search failed: {e}"

    if not results:
        return f"No results found for '{topic}'."

    lines = []
    for r in results:
        title = (r.get("title") or "").strip()
        url = (r.get("href") or "").strip()
        snippet = (r.get("body") or "").strip()
        page_text = _fetch_text(url) if url else ""
        lines.append(f"TITLE: {title}")
        lines.append(f"URL: {url}")
        if snippet:
            lines.append(f"SNIPPET: {snippet}")
        if page_text:
            lines.append(f"EXTRACT: {page_text}")
        lines.append("---")

    return "\n".join(lines)


def save_research_note(args: dict) -> str:
    title = (args.get("title") or "note").strip()
    content = args.get("content") or ""
    folder = os.path.expanduser(args.get("folder") or "notes")
    safe_title = re.sub(r"[^a-zA-Z0-9\\-_ ]+", "", title).strip().replace(" ", "_")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{ts}_{safe_title}.md")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Saved note: {path}"
    except Exception as e:
        return f"Couldn't save note: {e}"


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "research_topic",
            "description": "Web research pipeline: search for a topic, then fetch and extract plain text from top results. Returns sources with URLs and text extracts for summarization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic/question to research."},
                    "max_results": {"type": "integer", "description": "Number of search results (1-10)."},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_research_note",
            "description": "Save a research summary or notes as a markdown file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title."},
                    "content": {"type": "string", "description": "Markdown content."},
                    "folder": {"type": "string", "description": "Folder path to save into (default: notes)."},
                },
                "required": ["content"],
            },
        },
    },
]


DISPATCH = {
    "research_topic": research_topic,
    "save_research_note": save_research_note,
}
