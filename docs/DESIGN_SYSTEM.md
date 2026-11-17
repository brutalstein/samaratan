# Samaratan — Director’s Desk Design System

## Product identity

Samaratan is a **cinematic production workspace**, not a generic chat application. The design language takes cues from film title cards, production slates, director's notes, and editorial typography. It presents a clear next action with truthful progress and outputs.

## Principles

1. **Direct, don't prompt-engineer:** natural-language premise with optional genre sparks, minimal mandatory input.
2. **No fake results:** reference illustration is labelled concept art, the demo provider is explicitly deterministic, and native game builds only appear when created.
3. **One narrative source of truth:** engine-independent validated `GamePlan`; real scenes appear in production inspector.
4. **Keyboard and motion preferences:** Ctrl/Command+K focuses the brief, Escape dismisses overlay, focus is scoped to modal; `prefers-reduced-motion` disables animation.
5. **Accessible visual hierarchy:** semantic navigation, form labels, accessible state, focus outlines, explicit capability status, responsive 390px through desktop.

## Design tokens

- Background `#0b0e0d` — dark forest-black.
- Surface `#151a16` — warm graphite.
- Ink `#eeefe8` — cinematic parchment.
- Accent `#dce8ad` — pale signal lime.
- Gold `#dba984` — editorial amber.
- Serif: Instrument Serif (graceful Georgia fallback).
- UI sans: DM Sans (system sans fallback).

## UI architecture

The design is located under `samaratan/ui` and packaged with the Python distribution.

- `index.html` — semantic studio screens and form.
- `styles.css` — tokens, responsive system, motion, visual states.
- `app.js` — API client, router, production status polling, accessible forms, provider capability checks, historical archive, real GamePlan inspection, source/native download links.
- `noir-scene.svg` — original vector concept art, deliberately labelled **not generated gameplay**.

There is no paid UI library and no frontend build step. Optional CDN fonts degrade gracefully when offline.

## Workflow states

- `queued`: production received.
- `running`: agent planning and source generation.
- `succeeded`: actual archive/EXE links shown only when persisted by server.
- `failed`: inline error and route back to archive.
- `missing agent/engine`: choices are disabled or clearly marked.

## Future expansion

Design tokens and API calls are separated from layout. Future screens can add shot planning, asset research, voice casting, timeline editing and premium credit estimates without redesigning basic navigation.
