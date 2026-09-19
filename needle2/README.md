# Study File Agent — Needle 2 only

No RAG, no embeddings, no chat model, no OCR. Just Needle 2 (45M params,
~14MB, ~28MB RAM) deciding which of three file actions to take based on
what you type, then actually doing it on `I:\STUDY\STUDY\GCE AL 2027 EM`.

## What it can do
- **Find a file** — "where's my physics electromagnetic induction notes"
- **List recent files** — "what did I add this week"
- **Organize a file** — "move mechanics_notes.pdf into Physics"

It works on filenames and folder paths only — it doesn't open or read what's
inside a PDF/image, so it can't summarize content. Pure file lookup + tidy-up.

## Setup
1. `install.bat` — installs the one dependency (`cactus-needle`)
2. `python agent.py` — first run downloads Needle 2's weights (14MB, once)

## Notes
- If your folder path changes, edit `FOLDER_PATH` in `config.py`
- `move_file` needs an unambiguous filename match — if it finds more than
  one, it'll list them so you can be specific
