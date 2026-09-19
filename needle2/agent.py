"""
agent.py — Needle 2 only. No other model, no content reading, no OCR.

It works purely at the file level: finds files by name/path, lists recent
files, and moves/organizes files into subfolders. Needle 2 (45M params,
~14MB, runs locally) reads your plain-English request and decides which
of these three actions to take, filling in the arguments itself.
"""

import os
import shutil

import needle

try:
    from . import config as cfg
except ImportError:
    import config as cfg


def walk_files():
    for root, _dirs, files in os.walk(cfg.FOLDER_PATH):
        if "_rag_index" in root:
            continue
        for name in files:
            yield os.path.join(root, name)


@needle.tool
def find_files(keyword: str):
    """Find files in the study folder whose filename or folder path contains
    this keyword. Use this to locate notes, PDFs, past papers, or images by
    subject, topic, or partial name."""
    matches = [p for p in walk_files() if keyword.lower() in p.lower()]
    return matches[:30] if matches else f"No files matching '{keyword}'."


@needle.tool
def recent_files(count: int = 10):
    """List the most recently modified or added files in the study folder."""
    files = list(walk_files())
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files[:count]


@needle.tool
def move_file(filename: str, target_folder: str):
    """Move/organize a file into a subfolder of the study folder, e.g. moving
    a loose PDF into 'Physics', 'Chemistry', 'Biology', or 'Past Papers'.
    filename can be a partial match. Creates the target subfolder if needed."""
    matches = [p for p in walk_files() if filename.lower() in os.path.basename(p).lower()]
    if not matches:
        return f"No file found matching '{filename}'."
    if len(matches) > 1:
        return "Multiple matches, be more specific: " + ", ".join(matches[:10])

    src = matches[0]
    dest_dir = os.path.join(cfg.FOLDER_PATH, target_folder)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(src))
    shutil.move(src, dest)
    return f"Moved to {dest}"


agent = needle.Needle(tools=[find_files, recent_files, move_file])


def main():
    if not os.path.isdir(cfg.FOLDER_PATH):
        print(f"Folder not found: {cfg.FOLDER_PATH}")
        print("Edit FOLDER_PATH in config.py if your path is different.")
        return

    print(f"Watching: {cfg.FOLDER_PATH}")
    print("Ask to find, list, or organize files. Type 'exit' to quit.\n")

    while True:
        query = input("> ").strip()
        if query.lower() in ("exit", "quit"):
            break
        if not query:
            continue

        outcome = agent.run(query)
        for result in outcome.get("results", []):
            print(result)
        print()


if __name__ == "__main__":
    main()
