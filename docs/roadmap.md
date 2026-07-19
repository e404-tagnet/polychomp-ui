# Prism-UI Roadmap

## Completed
1. First-boot onboarding with 10-question survey
2. PRISM bias detection (24 biases, 6 routes)
3. Chat Analysis panel with metadata
4. Route guide sticky bar
5. Tiered memory (hot/warm/cool)
6. Project hierarchy (overview/plan/review tabs)
7. Plugin system with 4 built-in plugins
8. Skill Builder and Tool Builder pages
9. Workspace folder linking
10. Desktop icons and launcher
11. Settings modal with tabs
12. Icon rail sidebar

## In Progress / Planned

### Auth Upgrade (C to B)
Current: file-based profile ID + simple password flag (Option C)
Target: session token continuity with in-memory token dict (Option B)
Blockers: none
Effort: low

### Independent Bias Audit
Current: plugin scaffold created (tool-bias-audit)
Target: wire into Chat Analysis panel to display AI bias alongside user bias
Blockers: frontend panel needs ai_audit rendering
Effort: medium

### Embedding-Based Classifier
Current: keyword-only (24 biases)
Target: hybrid embedding classifier for 100+ biases with one vector search
Blockers: needs Ollama embed endpoint integration
Effort: medium

### Benchmarks
Current: latency/accuracy script created
Target: CI integration and regression tracking
Blockers: none
Effort: low

### Screenshots and Docs
Current: main dashboard captured
Target: Settings, Memory, Analysis, Chat with bias badges
Blockers: browser JS modal triggering
Effort: low

## Long Term
* Multi-project sync across devices
* Tagnet.net deploy with tunnel
* 10+ scaffold plugin ecosystem
* Novel tiered memory/storage research
