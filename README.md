# Samaratan Studio

**Agent-native cinematic game production — local-first developer foundation.**

Samaratan is building toward a browser-based studio that lets non-programmers design narrative, cinematic single-player games and receive downloadable native builds. The first milestone is a **real, testable production pipeline**, not a fabricated AAA demo.

## Current status

| Capability | Status |
|---|---|
| Director’s Desk cinematic editorial interface, story inspection, archive, provider status | Implemented |
| Versioned `GamePlan` with validated branching narrative graph | Implemented |
| Deterministic no-network demo director | Implemented |
| Claude Code CLI / Codex CLI agent adapters | Implemented; real account testing required |
| Godot 4 source generation (playable placeholder 3D + dialogue decisions) | Implemented; engine runtime testing required |
| Godot Windows export adapter | Implemented; requires a Godot 4 binary + Windows export templates on build machine |
| SQLite job persistence, isolated workspaces, source ZIP download | Implemented |
| Photorealistic cinematics, MetaHuman, Unreal, premium model hub | **Not yet implemented** |
| Cloud build workers, billing, multi-tenant accounts | **Not yet implemented** |

## Quick start (Windows PowerShell)

Requires Python 3.11+. **No Unreal installation, API key, credit purchase or Godot installation needed to run the demo and download a real engine project.** Godot is only required if you want to run/export the generated game.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
samaratan
```

Open **http://127.0.0.1:8765**. Choose `Deterministic demo (free)`, submit a game idea and download `game-source.zip`.

For actual model-directed story generation, install the official `codex` or `claude` CLI, sign into your own account **locally** and choose it from the web UI. Credentials are **never** entered into Samaratan. Supported CLI argument sets may need adaptation as the vendor tools evolve; live integrations have not yet been verified with authenticated subscriptions.

### Native Windows `.exe`

Install Godot 4 and its matching **Windows Desktop export templates on the build machine**; configure `SAMARATAN_GODOT_BINARY` if `godot` is not on `PATH`. Then check the **Export Windows .exe** option. A successful result exposes an executable download. Without Godot, requesting an `.exe` returns an explicit failure rather than a fake download. Source generation still works with no engine installed. The commercial design moves build workers off the customer's machine.

The interface uses a custom self-hosted design system with responsive layouts, reduced-motion support, and no JavaScript UI framework. The hero illustration is clearly labelled concept art; it is not a game render. The UI is bundled as Python package data under `samaratan/ui`.

## Tests

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Architecture

- **Contract-first:** validated, engine-independent `GamePlan` JSON and scene graph.
- **Providers:** deterministic demo and opt-in authenticated Codex/Claude CLI subprocess adapters; no shell commands or subscription sharing.
- **Engine plugins:** initial Godot adapter, extendable to Unreal when a genuine build worker exists.
- **Orchestration:** isolated generation jobs, local SQLite ledger and ZIP artifacts.
- **Web:** dependency-free browser interface backed by same-origin API; no credit or GPU-cloud requirement.

See [architecture](docs/ARCHITECTURE.md) and [milestones](docs/ROADMAP.md). This repo is an engineering starting point, not a completed photorealistic game generator.
