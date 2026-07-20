# Prism-UI Session Handoff — 2026-07-20

## Project State

**Repo:** `e404-tagnet/polychomp-ui` (branded as Prism-UI, slug kept for continuity)
**Local path:** `/home/e404/Dropbox/9-PROJECTS/polychomp-ui/`
**Backend:** FastAPI on `http://127.0.0.1:8788` (HTTP, no SSL)
**Frontend:** Vanilla JS served from `frontend/`
**PRISM source:** `/home/e404/Dropbox/9-PROJECTS/prism-scaffold/src` (must stay on PYTHONPATH)
**Server command:** `cd backend && PYTHONPATH=/home/e404/Dropbox/9-PROJECTS/prism-scaffold/src:$PYTHONPATH python3 main.py`

## What Is Done

1. **Backend:** FastAPI with PRISM pipeline integration, plugin hooks, Ollama chat, Memory API, Workspace API with path validation (restricted to `/home/e404/Cloud/WORKSPACES/prism-ui-workspace`), ProjectContext/SubChat models
2. **Frontend:** Icon rail, Chat Analysis panel, route guide, tiered memory panel, workspace bar, project tabs (Chat/Overview/Plan/Review), settings modal with tabs, plugin manager, onboarding modal, help modal, chat options dropdown
3. **PRISM bias detection:** 24 biases via keyword classifier, 6 routes, dynamic temperature. Benchmark: 100% accuracy, 0.49 ms avg
4. **Plugin system:** 4 built-in plugins — `scaffold-prism`, `skill-summarize`, `tool-web-search`, `tool-bias-audit`
5. **AI Self-Audit:** Bias audit plugin catches sycophancy/overconfidence/courtesy/anchoring in AI responses, rendered in Chat Analysis panel
6. **Builder pages:** `/skill-builder` (SKILL.md wizard) and `/tool-builder` (HTML artifact reference) served as static pages
7. **Desktop integration:** `prism-ui-launcher.sh` with isolated Brave profile, `tagnet.desktop` using `tagnet-launcher.sh`
8. **Onboarding:** 10-question survey with system prompt tree (expert textarea vs 5-question guided)
9. **Tagnet.net rebrand:** All Polychomp references scrubbed, local link switched to HTTP
10. **Docs:** README.md, docs/roadmap.md, scripts/benchmark.py

## Recent Commits (newest first)

- `6c4a08f` fix: rail buttons e.preventDefault, all event listeners null-safe
- `8eb2206` fix: icon rail how-to, new-memory, workspace buttons wired correctly
- `4b3caa0` feat: AI self-audit rendered in Chat Analysis panel
- `22b7c06` feat: bias audit plugin, README, benchmark, roadmap
- `eb9ad8f` fix: builder routes, FileResponse import, HTTP-only, Prism-UI title
- `d2ccd0d` feat: rail JS, memory textarea+dropdown, tooltip CSS, bias expansion
- `438e592` feat: project hierarchy backend+frontend, ProFont icons

## Known Issues / Decisions Needed

1. **Full-screen app window:** Brave Flatpak refuses `--app=` for `http://` localhost. Current workaround: isolated profile opens as normal browser window. Options: accept it, switch to Chromium Flatpak, or package as AppImage/Electron (discussed — user prefers browser for now)
2. **Auth upgrade:** Currently Option C (file-based profile ID). Roadmap has Option B (session token continuity) as planned work
3. **Rename projects/chats:** User wants this feature — not yet implemented, on roadmap
4. **Screenshots:** Folder `/home/e404/Dropbox/9-PROJECTS/polychomp-ui/screenshots/` ready but empty. User was going to capture them
5. **Hermes update:** User mentioned Hermes (this system) needs an update — action pending

## File Quick Reference

| File | Path | Purpose |
|------|------|---------|
| Backend entry | `backend/main.py` | FastAPI server, all endpoints |
| Plugin manager | `backend/plugin_manager.py` | Discovery, hooks, state |
| Frontend logic | `frontend/js/app.js` | All UI interaction |
| Frontend styles | `frontend/css/style.css` | Catppuccin Mocha theme |
| Frontend shell | `frontend/index.html` | DOM structure |
| Skill Builder | `frontend/skill-builder.html` | Attached file, now served |
| Tool Builder | `frontend/tool-builder.html` | Attached file, now served |
| Bias classifier | `prism-scaffold/src/prism/classifiers/keyword.py` | 24 bias keyword maps |
| Route selector | `prism-scaffold/src/prism/classifiers/selector.py` | Bias-to-route mapping |
| Benchmark | `scripts/benchmark.py` | Latency/accuracy test |
| Roadmap | `docs/roadmap.md` | Planned work |

## User Preferences (from memory)

- Catppuccin Mocha dark mode, teal `#89dceb` + sky `#94e2d5` accents
- No emojis, no `---` horizontal rules, generic language in published docs
- ProFontWindows Nerd Font Bold for desktop icons (thick P+ui, T+n)
- Workspace linking over file upload, restricted to `/home/e404/Cloud/WORKSPACES/prism-ui-workspace`
- Local-first, static GH Pages for public sites
- SHA-256 client-side password gates on static pages
- No sycophancy in evaluations — wants honest assessment
- Bias badges in CAPS under user messages

## How to Resume

1. Ensure Ollama is running (`ollama list` to check)
2. Start backend: `cd backend && PYTHONPATH=/home/e404/Dropbox/9-PROJECTS/prism-scaffold/src:$PYTHONPATH python3 main.py`
3. Open `http://127.0.0.1:8788` in Brave
4. Run `scripts/benchmark.py` to verify PRISM health
5. Check `docs/roadmap.md` for next priorities
