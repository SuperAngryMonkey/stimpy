# Changelog — Stimpy

All notable changes to this project are documented here.
Format loosely follows Keep a Changelog. Dates are ISO 8601.

## [0.2.0] — 2026-10-29

### Added
- Delivery: `?mode=delivery` on /order, /dryrun, /specials; delivering store
  auto-resolved from the locator (or `DELIVERY_STORE_ID`); tip from
  `DELIVERY_TIP`; `/dryrun` reports `due` = quote + tip.
- Card / gift-card payment: `?pay=card|giftcard`, read from
  `payment_local.py` only (ADR 0004). `set_payment.py` interactive setup
  (masked, Luhn/type-checked, writes 0600). `payment.scrub()` on every
  Domino's response. `.githooks/pre-commit` digit-run guard.
- ren MCP: `mode` and `pay` args on pizza_dryrun / pizza_order / pizza_specials.
- `ADDR_TYPE`, `ADDR_UNIT`, `DELIVERY_STORE_ID` optional in config_local.py.

### Changed
- ADR 0002 superseded by ADR 0004; defaults (carryout, cash) unchanged.
- `place_order` bypasses pizzapi `Order.place()` (which resets Payments to Cash).

## [0.1.0] — 2026-05-27

### Added
- Initial proof of concept.
- Single-page Flask app with one order button and a dry-run button.
- `pizzapi` integration with workarounds for: missing User-Agent (403
  defense), no-op topping options, and Delivery-default service method.
- Hardcoded canonical order: Medium Handmade Pan (`P12IPAZA`) + ham (`H`)
  + pineapple (`N`), carryout from store 3891, cash at pickup.
- Debug `/menu` route for re-verifying product codes from the LXC.
- `/health` route with Domino's reachability check.
- `/dryrun` route — validate + price without placing.
- systemd unit with basic hardening.
- Full doc suite (README, HANDOFF, SECURITY, DESIGN, OPERATIONS, ADRs).

### Verified
- Store 3891 reachable from target LXC (HTTP 200).
- All product/topping codes read from live menu.
