# HANDOFF — Stimpy

**Status:** Built, deployable. Order construction verified by syntax + logic
review. End-to-end validation pending first dry run on the target LXC.

## Current state

- Flask single-page app, complete.
- Order logic wraps `pizzapi` with three workarounds (UA injection, manual
  topping options, carryout override) — see DESIGN.md.
- All order codes confirmed against live menu for store 3891 (2026-05-27):
  pizza `P12IPAZA`, ham `H`, pineapple `N`.
- Target: LXC 206 (`stimpy`) on **proxlab** (`10.0.1.9` / TS `100.105.71.57`),
  Debian 12, residential IP. Domino's reachability confirmed (HTTP 200 from
  store-locator on 2026-05-27).

> **2026-07-20 correction:** Stimpy's actual Tailscale IP is `100.84.231.64`
> (verified from proxlab via `pct exec 206 -- tailscale ip -4`). The
> `100.105.71.57` above is stale. Container is running; app is not
> daemonized yet — `stimpy.service` exists in `/opt/stimpy/` but isn't
> installed to systemd or started. Next session: install the unit and
> flip Heimdall's `/dominos` route to `enabled: true`.

## What works

- Modules compile clean.
- Store 3891 reachable from the target box (verified via curl).
- Menu pull verified (245KB, parses, codes extracted).

## What is NOT yet verified

- A live `/dryrun` from the LXC (validate + price round trip). This is the
  first thing to do after deploy. It exercises the whole stack without
  placing an order.
- An actual placed order. Only do this when you genuinely want the pizza.

## Next steps (in order)

1. Deploy per OPERATIONS.md.
2. `curl -X POST http://localhost:5000/dryrun` — expect `{"ok":true,...}`
   with a price. If it 403s, the box lost Domino's reachability (unlikely,
   it was 200). If it fails validation, re-check codes via `/menu?q=pan`.
3. When ready for a real pizza: press **Feed Me**, confirm the dialog.

## Known open questions

- Domino's may treat a brand-new customer + address combo with extra
  scrutiny on first real order. If the first `/order` is rejected where
  `/dryrun` passed, that's the likely cause — worth a manual order through
  their site once to "seed" the customer record.
- No persistence: "last order" resets on service restart (by design, POC).

## Future (deliberately out of scope)

- Order history / true "repeat last order" (would need local SQLite).
- Live order tracking via the pizza tracker API.
- Multiple saved orders / a second button.
