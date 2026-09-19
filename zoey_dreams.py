"""Local dream processing for ZOEY's sleep cycle.

This first version is deliberately deterministic: it can run offline and does
not pretend that keyword overlap is semantic understanding. A future model-
assisted pass can enrich the same morning-brief format.
"""

import collections
import re
import time
from datetime import datetime, timedelta

import brain_store


_STOPWORDS = {
    "about", "after", "again", "also", "been", "but", "can", "could",
    "from", "have", "hello", "into", "just", "like", "more", "need",
    "only", "that", "the", "their", "them", "then", "there", "this",
    "what", "when", "where", "with", "would", "your", "zoey",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9']{2,}", text.lower())
    return {word for word in words if word not in _STOPWORDS}


def load_recent_memories(hours: int = 24) -> list[dict]:
    cutoff = time.time() - (max(1, hours) * 60 * 60)
    path = brain_store.path_for("memory.jsonl")
    items = []
    for item in brain_store.iter_jsonl(path):
        if not isinstance(item, dict) or item.get("type") != "memory":
            continue
        try:
            if float(item.get("ts", 0)) >= cutoff:
                items.append(item)
        except (TypeError, ValueError):
            continue
    return items


def _clusters(memories: list[dict]) -> list[list[dict]]:
    clusters = []
    for memory in memories:
        words = _tokens(memory.get("text", ""))
        best = None
        best_overlap = 0
        for cluster in clusters:
            cluster_words = set().union(*(_tokens(x.get("text", "")) for x in cluster))
            overlap = len(words & cluster_words)
            if overlap > best_overlap:
                best = cluster
                best_overlap = overlap
        if best is not None and best_overlap >= 1:
            best.append(memory)
        else:
            clusters.append([memory])
    return [cluster for cluster in clusters if len(cluster) >= 2]


def _make_insights(clusters: list[list[dict]]) -> list[str]:
    insights = []
    for cluster in clusters:
        counts = collections.Counter()
        for memory in cluster:
            counts.update(_tokens(memory.get("text", "")))
        themes = [word for word, count in counts.most_common(3) if count >= 2]
        if themes:
            insights.append(
                "A recurring thread appeared around " + ", ".join(themes) +
                f" ({len(cluster)} related memories)."
            )
    return insights[:8]


def queue_morning_brief(insights: list[str], source: str = "dream_cycle") -> None:
    for insight in insights:
        brain_store.add_morning_brief(insight, tags=["dream", "morning_brief"], source=source)


def dream_cycle(hours: int = 24) -> dict:
    """Consolidate recent memories and queue a brief for the next wake cycle."""
    memories = load_recent_memories(hours=hours)
    clusters = _clusters(memories)
    insights = _make_insights(clusters)
    if insights:
        queue_morning_brief(insights)
    brain_store.record_dream_run(
        memories_seen=len(memories),
        clusters_found=len(clusters),
        insights_created=len(insights),
    )
    return {
        "memories_seen": len(memories),
        "clusters_found": len(clusters),
        "insights_created": len(insights),
        "insights": insights,
        "ran_at": datetime.now().isoformat(timespec="seconds"),
    }


def get_morning_brief(limit: int = 5) -> list[dict]:
    return brain_store.recent_records("morning_brief.jsonl", limit=limit)
