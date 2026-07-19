# Prism-UI

A local-first AI workbench with PRISM bias detection, tiered memory, plugin architecture, and project hierarchy. Runs entirely on your machine with Ollama.

## Stack

* FastAPI backend with PRISM scaffold integration
* Vanilla JS frontend, no build step
* Ollama for local LLM inference (phi4-mini default)
* PRISM for cognitive-bias detection and routing
* SQLite-free JSON project storage

## Features

### Bias Detection & Routing
PRISM keyword classifier detects 24 cognitive biases in real time, maps each to one of 6 interaction routes (comply, challenge, clarify, encourage, digress, end), and adjusts temperature dynamically. Biases detected include anchoring, confirmation, sunk cost, availability, bandwagon, blind spot, gambler fallacy, status quo, stereotyping, and more.

### Chat Analysis Panel
Hidden-by-default inspector showing per-message PRISM metadata: detected bias, confidence, chosen route, temperature, token estimate, and latency. Toggle with the Analysis button.

### Route Guide
Sticky reference bar above the chat showing all 6 routes with color-coded dots and plain-text tooltips.

### Tiered Memory
Hot, warm, and cool memory tiers with automatic decay (hot to warm after 24 hours, warm to cool after 1 week) and promotion via access count. Users can add memories with an impression dropdown; AI makes the final placement decision.

### Project Hierarchy
Every project has Chat, Overview, Plan, and Review tabs that evolve as the project grows. Sub-chats supported via the project model.

### Icon Rail
Far-left sidebar with 8 shortcuts: Projects, Skill Builder, Tool Builder, How-To Guide, Docs, New Memory, Workspace Folder, and Tagnet Dashboard. Each opens its target or a modal.

### Plugin Manager
Tabbed modal (All, Scaffolds, Skills, Tools) with plugin cards, type-colored badges, and live toggle switches. Three built-in examples included: scaffold-prism, skill-summarize, tool-web-search, plus the new tool-bias-audit.

### Skill Builder & Tool Builder
Built-in wizard pages for authoring SKILL.md files and building HTML artifact tools. Accessible from the icon rail.

### Workspace Linking
Link any folder under your assigned workspace path. Files appear as clickable chips under the chat header; clicking injects a 2 KB snippet into the chat input. Read-only, never writes.

### Onboarding
10-question first-boot survey that feeds into scaffold parameters. Auto-creates a Welcome project with system-tip messages.

### Settings
Tabbed modal (General, Plugins, Memory, About) with model selector, Creativity slider (temperature 0 to 1), and system prompt builder. Two modes: empty textarea for experts, or a 5-question guided builder for everyone else.

### Desktop Integration
Periodic-table-style SVG icons (ProFontWindows Nerd Font Bold) in teal and sky on a dark gradient. Brave browser launches in app mode via `prism-ui-launcher.sh`.

## Run Locally

```bash
cd backend
PYTHONPATH=/path/to/prism-scaffold/src:$PYTHONPATH python3 main.py
```

Open http://127.0.0.1:8788 in Brave app mode (see `prism-ui-launcher.sh`).

## Repo

https://github.com/e404-tagnet/polychomp-ui

## License

MIT
