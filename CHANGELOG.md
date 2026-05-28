# Changelog — Stimpy

All notable changes to this project are documented here.
Format loosely follows Keep a Changelog. Dates are ISO 8601.

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
