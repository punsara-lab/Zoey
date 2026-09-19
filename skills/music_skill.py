import re
import time
import urllib.parse
import webbrowser

import requests


def open_youtube_music(_args: dict) -> str:
    webbrowser.open("https://music.youtube.com/")
    time.sleep(1.5)
    return "Opened YouTube Music."


def play_youtube_music(args: dict) -> str:
    query = (args.get("query") or "").strip()
    if not query:
        webbrowser.open("https://music.youtube.com/")
        time.sleep(1.5)
        return "Opened YouTube Music. Tell me what to play."

    q = urllib.parse.quote_plus(query)
    search_url = f"https://www.youtube.com/results?search_query={q}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    }
    video_id = None
    try:
        r = requests.get(search_url, headers=headers, timeout=8)
        if r.status_code == 200:
            m = re.search(r"\"videoId\":\"([a-zA-Z0-9_-]{11})\"", r.text)
            if m:
                video_id = m.group(1)
    except Exception:
        video_id = None

    if video_id:
        url = f"https://music.youtube.com/watch?v={video_id}&autoplay=1"
        webbrowser.open(url)
        time.sleep(1.5)
        return f"Playing on YouTube Music: {query}"

    webbrowser.open(f"https://music.youtube.com/search?q={q}")
    time.sleep(1.5)
    return f"Opened YouTube Music search for: {query}"


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "open_youtube_music",
            "description": "Open YouTube Music in the default browser.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_youtube_music",
            "description": "Search and play a song on YouTube Music using the default browser (best-effort).",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "What to play."}},
                "required": ["query"],
            },
        },
    },
]


DISPATCH = {
    "open_youtube_music": open_youtube_music,
    "play_youtube_music": play_youtube_music,
}

