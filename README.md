# Polychomp-UI

A scaffold-first chat GUI for local and remote LLM conversations, built around the PRISM shadow Bayesian scaffold. Named after the many-toothed beast that devours context — and gives it back, structured.

## What It Does

- **Project-centric workspaces** — each project has isolated session memory + shared core memory
- **PRISM shadow analysis** — every user message gets bias classification, route suggestion, and session metrics (hidden-by-default inspector panel)
- **Adaptive behavior** — PRISM adjusts temperature, assertiveness, and routing based on conversation phase and inferred outcomes
- **Model routing** — local (Ollama) or cloud, per-project or per-message, with privacy tier selection
- **Catppuccin Mocha** dark mode with teal and sky accents

## Quick Start

```bash
cd poly-chomp-ui/backend
pip install -r requirements.txt
PYTHONPATH=/path/to/prism-scaffold/src:$PYTHONPATH uvicorn main:app --host 0.0.0.0 --port 8788
```

Open `http://127.0.0.1:8788` in your browser.

Requires:
- Python 3.11+
- [PRISM](https://github.com/e404-tagnet/prism) cloned and on `PYTHONPATH`
- Ollama running locally (for LLM inference)

## Architecture

```
poly-chomp-ui/
├── backend/
│   ├── main.py              # FastAPI server
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Single-page app
│   ├── css/style.css        # Catppuccin Mocha theme
│   └── js/app.js            # Vanilla JS frontend
└── projects/                # Local project stores (JSON)
```

## PRISM Inspector

Click the PRISM chip on any user message to open the inspector panel:
- Detected bias + confidence
- Recommended route + reasoning
- Session metrics (temperature, assertiveness, topic drift, factual lock)

## Privacy Modes

| Mode | Behaviour |
|---|---|
| **Local** | PRISM + LLM both run on your machine. No data leaves. |
| **Hybrid** | PRISM runs locally; LLM can be cloud-routed per project/message. |
| **Cloud** | Both PRISM and LLM can run remotely (for tagnet.net deploy). |

## License

MIT — the scaffold is yours, the monsters are mythical.
