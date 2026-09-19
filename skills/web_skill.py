"""
ZOEY — skills/web_skill.py
Gives ZOEY the ability to actually research something, not just answer
from the brain model's training data. Uses DuckDuckGo search (free, no
API key) via the `ddgs` package.
"""

import json
import privacy


MAX_RESULTS = 5


def web_search(args: dict) -> str:
    query = args.get("query", "")
    if not query:
        return "No search query given."
    if not privacy.allow_external("web"):
        return "Web search is blocked by PRIVACY_MODE=local. Enable online access explicitly to search the web."

    try:
        from ddgs import DDGS
    except ImportError:
        return (
            "Web search isn't available — the 'ddgs' package isn't installed. "
            "Run: pip install ddgs"
        )

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(privacy.sanitize_text(query), max_results=MAX_RESULTS))
    except Exception as e:
        return f"Search failed: {e}"

    if not results:
        return f"No results found for '{query}'."

    items = []
    for r in results:
        title = r.get("title", "").strip()
        snippet = r.get("body", "").strip()
        url = r.get("href", "").strip()
        if title or snippet or url:
            items.append({"title": title, "snippet": snippet, "url": url})

    return json.dumps(
        {"type": "web_search_results", "query": query, "results": items},
        ensure_ascii=False,
    )


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information — use this for anything that needs up-to-date facts, not just what you already know.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"],
            },
        },
    },
]

DISPATCH = {
    "web_search": web_search,
}
