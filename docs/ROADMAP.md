# Delivery milestones

## M0 — verifiable local foundation (this commit)
- [x] Source-controlled architecture, docs and CI
- [x] Responsive local browser studio and typed API
- [x] GamePlan v1 contract, branch validation and narrative demo director
- [x] Local CLI adapters for account-authenticated Codex and Claude Code (unit-tested, not authenticated live-tested)
- [x] Godot engine adapter: source project generator and optional Windows export command
- [x] Source ZIP artifacts, job ledger, per-job directory isolation and tests
- [ ] Actual engine runtime visual/playability acceptance test on Godot 4
- [ ] Actual Windows .exe compilation acceptance test

## M1 — first real game vertical slice
- Camera and character controller with world geometry and dialogue choices tested interactively
- Visual regression test images and runtime smoke tests on CI with pinned Godot version
- Scene asset manifest, asset source metadata and build reproducibility
- Safe asset ingestion, import transformations and licenses/attribution registry
- CLI provider live tests with owner's authenticated local sessions

## M2 — agent-native production
- Versioned Story-to-Game intermediate representation with state machines and quest logic
- Procedural staging, cinematics, voice/face-animation adapters
- Deterministic compiler snapshots, rollback, semantic scene diff and playtest evaluation
- Godot-to-Unreal is **not** automatic; build a separate native Unreal adapter and compare outputs

## M3 — hosted studio (requires infrastructure budget)
- Auth, organisations, per-tenant isolation, independent build workers, signed downloads
- Provider-approved commercial API integrations, prepaid credits and budget caps
- Windows game binary signing, malware scanning, asset provenance and paid model cost accounting

**Release gate:** A user can describe a branching single-player story in browser UI and obtain a reproducible native Windows executable from a build worker, with logs and real runtime tests. Until then, describe the platform as a foundation, not completed AAA production.
