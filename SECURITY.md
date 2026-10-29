# SECURITY — Stimpy

> *"Quis custodiet ipsos custodes?"* applies to anything that spends your
> money on a button press. Read this before exposing the app anywhere.

## Threat model in one line

This app places real, money-costing orders on an unauthenticated button
press. The only safety rails are a browser confirm dialog and the fact that
payment defaults to cash-at-pickup. Since ADR 0004 a card or gift card MAY
be configured on the host; if so, `pay=card` orders are real charges.

## What this app does NOT handle

- **No card data over the wire or in the repo.** A card may exist ONLY in
  `payment_local.py` (gitignored, 0600, service-user owned, written by
  `set_payment.py`). No route, MCP tool, env var or config field accepts a
  card number; responses are scrubbed (`payment.scrub`) before logging;
  a pre-commit hook blocks digit runs. Prefer a gift card. See ADR 0004.
- **No login / no auth.** Anyone who can reach port 5000 can order a pizza on
  your dime. This is acceptable ONLY because the app is bound to a private
  LXC on your home network / tailnet.

## Exposure rules

- **DO** keep it on the LAN or tailnet (`100.x` / `10.x`). Reach it over
  Tailscale, not the public internet.
- **DO NOT** put it behind Funnel, a public reverse proxy, or any
  internet-facing route. A single curl from a stranger = a pizza you didn't
  order and have to refuse at the counter.
- If you ever need remote access, gate it behind Tailscale ACLs, not exposure.

## Stored secrets

- None. There are no API keys, tokens, or passwords. The unofficial Domino's
  API requires no authentication — that is precisely why guarding network
  exposure matters.

## PII

- `config.py` contains your name, email, phone, and address in plaintext.
  This is necessary for the order and is no more sensitive than a saved
  Domino's profile — but it means `config.py` should not be committed to a
  public repo. Keep the repo private, or template `config.py` and gitignore
  the real one. (Currently committed for the POC; the repo is assumed
  private.)

## Abuse / accident surface

- The confirm dialog is the last line before a real order. The `/order` route
  has no rate limit — repeated POSTs place repeated orders. Don't script
  against it.
- `/dryrun` is safe to hammer; it never places.

## Hardening present

- systemd unit runs as unprivileged `stimpy` user with `NoNewPrivileges`,
  `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`.

## PII split (2026-08-05)

Customer identity (name, address, phone, email) lives in config_local.py,
which is gitignored. The repo tracks config_local.example.py with placeholder
values only. Commits before 2026-08-05 predate this split and contain the
old hardcoded identity; the repo is private and stays private unless history
is rewritten.
