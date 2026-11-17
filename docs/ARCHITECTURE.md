# Samaratan architecture — engineering decision record 0001

## Product boundary

**Authoring surface** is the browser. **Build workers** generate native engine packages. **Games run on players' own hardware**, without streaming or subscriptions after download. The local workstation simulates the eventual build-worker deployment, not a mandatory install for future customers.

## Modules

```text
Browser UI (web/index.html)
        |
FastAPI typed HTTP API (samaratan/api.py)
        |
SQLite job ledger (store.py) -- one directory per opaque job ID
        |
Job orchestrator (service.py)
        |                         \
Provider contract (providers.py)    Engine contract (godot.py)
  | demo | codex | claude             | Godot4 | future Unreal build service
        \                         /
         GamePlan v1 (models.py)
                  |
          ZIP artifact / Windows .exe if truly compiled
```

## Model strategy

The AI receives a bounded narrative-authoring task with an exact JSON contract. The model does **not** return an arbitrary shell script or executable code for a build worker. GDScript generation in this milestone is deterministic from a reviewed template. Future semantic actions will require policy-gated engine tools and explicit user confirmation for privileged operations. Personal subscription CLI support is for local owner-operated prototyping; a future multi-user commercial SaaS requires vendor-approved API integrations and separate tenant isolation.

## Security invariants

1. Agent subprocesses are invoked with fixed argv, `shell=False`, isolated temporary cwd and timeout. Output size and schema are bounded; errors do not echo CLI credentials.
2. Job IDs are UUID hex strings and mapped to isolated folders; artifact download paths are resolved and constrained to the job folder.
3. No API endpoint accepts arbitrary command, executable path, filesystem path, or uploaded archive.
4. Story schema rejects extra fields, unknown scene links, duplicate IDs and unreachable scenes.
5. The development server binds to loopback by default. It is NOT hardened or authenticated for public hosting.

## Known limitations

- Godot source generation is **not Unreal photorealism** and is intentionally a lightweight interactive narrative placeholder.
- CLI account sign-in must be performed by the owner outside Samaratan.
- Only a local process manages jobs. Future distributed queues require leases, retries, idempotency and durable object storage.
- The first HTML user interface has no collaborative editors, sessions, auth or asset pipeline.
- Real .exe export requires native engine installation on the **worker**, and export templates; no headless engine is available in this tool environment.

## Extension contracts

Future providers implement `generate(prompt) -> GamePlan`. Future engine adapters implement `generate(GamePlan, directory) -> Path`, `bundle(...)`, `export_windows(...)`. Additional game capabilities should be layered as schema-versioned actions, not silent engine-specific fields in `GamePlan`.
