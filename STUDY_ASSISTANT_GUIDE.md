# ZOEY Study Assistant - Quick Reference

## What It Does

The Study Assistant connects Zoey to your research workflow:
- **Study Sessions**: Track what you're learning with timed sessions
- **Deep Research**: Multi-step research with AI synthesis
- **Google Colab**: Launch notebooks directly
- **External AI**: Call specialized AIs (Claude, Perplexity, Wolfram) for specific tasks
- **Note Export**: Export to Markdown, Anki flashcards, or PDF

---

## Quick Commands (Say These to Zoey)

### Start Studying
```
"Zoey, start a study session on machine learning"
"Start studying Python for 60 minutes"
"Begin study session: neural networks"
```

### During Study
```
"Add a note: Python uses indentation for blocks"
"Note this down: Key concept - backpropagation"
"Save this as a question: What is gradient descent?"
```

### Research
```
"Research: attention mechanism in transformers"
"Deep research on quantum computing"
"Search and synthesize latest on LLMs"
```

### Google Colab
```
"Open Colab"
"Create a new notebook for studying calculus"
"Open notebook in Colab"
```

### Call External AI
```
"Ask Claude to explain this code"
"Use Perplexity to research this topic"
"Wolfram: solve integral of x^2"
"Call external AI to help with this math problem"
```

### End & Export
```
"End study session"
"Export my notes to Anki"
"Save study session as PDF"
"Export to markdown"
```

---

## Available Tools (How They Work)

### 1. **start_study_session**
Creates a tracked study session with:
- Topic and goal
- Start time
- Duration tracking
- Note collection

### 2. **add_study_note**
Add notes during study:
- Types: general, question, key_point, definition, example
- Timestamps
- Source tracking

### 3. **deep_research**
Multi-step research workflow:
1. Web search for current info
2. AI synthesis of findings
3. Structured notes saved

### 4. **open_colab / create_study_notebook**
Google Colab integration:
- Open new/existing notebooks
- Create study templates
- Auto-format for Colab

### 5. **call_external_ai**
Call specialized AI services:
- **Claude**: Code, reasoning, writing
- **Perplexity**: Research, citations
- **Wolfram**: Math, computation
- **Auto**: Route based on query type

### 6. **export_study_notes**
Export to:
- **Markdown**: Full session notes
- **Anki**: Flashcards for spaced repetition
- **PDF**: Formatted document

---

## Study Workflow Example

```
User: "Zoey, start a study session on machine learning"
Zoey: "Started study session: Machine Learning. Goal: Learn and understand the topic..."

User: "Research: transformer architecture"
Zoey: [Performs deep research, searches web, synthesizes with AI, saves notes]

User: "Add note: Transformers use self-attention mechanism"
Zoey: "Added key_point note to study session."

User: "Open Colab and create a notebook for practicing transformers"
Zoey: "Created study notebook. Open in Colab?"

User: "Ask Claude to explain the attention formula"
Zoey: [Calls Claude API, returns explanation]

User: "End study session"
Zoey: "Session complete! 45 minutes, 5 notes, 1 research topic. Export options: Anki, PDF, Markdown"
```

---

## API Keys Required

Add these to your `.env` file:

```bash
# For research & external AI
ANTHROPIC_API_KEY=your_key_here      # For Claude
PERPLEXITY_API_KEY=your_key_here     # For Perplexity
WOLFRAM_APP_ID=your_app_id_here      # For Wolfram Alpha

# OpenRouter is already configured for main Zoey
OPENROUTER_API_KEY=your_key_here
```

---

## Notes

- All study data is saved locally in `~/zoey_studies/`
- No data is sent to external services without explicit commands
- External AI calls are routed through your chosen privacy settings
- Google Colab requires browser permissions

---

**Happy Studying! 📚🎓**
