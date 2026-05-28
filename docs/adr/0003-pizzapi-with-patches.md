# ADR 0003 — Use pizzapi, patched, rather than raw API calls

**Status:** Accepted
**Date:** 2026-05-27

## Context

The Domino's "power" API can be called directly (raw JSON) or via the
`pizzapi` wrapper. The wrapper handles store/menu/order object modeling but
has known gaps.

## Decision

Use `pizzapi` and work around its three quirks in `order_logic.py` rather than
reimplementing the API client from scratch:

1. Monkeypatch `requests` to inject a browser User-Agent (defeats 403s).
2. Inject topping `Options` manually (library's `options=` arg is a no-op).
3. Override `ServiceMethod` to Carryout (library defaults to Delivery).

## Consequences

- (+) Far less code than a hand-rolled client; reuses tested object modeling.
- (+) Workarounds are isolated in one module, clearly commented.
- (-) Depends on an unmaintained-ish library; a future Domino's API change
  could require dropping to raw calls. The `/menu` route and isolated
  workarounds make that migration tractable.
- (-) Monkeypatching `requests` globally is a blunt instrument; acceptable in
  a single-purpose process.
