# ADR 0004 — Delivery and card payment, card held locally only

**Status:** Accepted — supersedes ADR 0002
**Date:** 2026-10-29

## Context

ADR 0002 chose Carryout + Cash to keep card data out of an unauthenticated
POC. That held for five months. The user now wants delivery, which Domino's
will not do for cash in practice, and wants a card on the appliance. The
trade is understood: the number lives on a LAN host, and a compromise of
that host exposes it.

## Decision

1. Service method and payment type become **per-request parameters**
   (`?mode=carryout|delivery`, `?pay=cash|card|giftcard`) with defaults
   that preserve ADR 0002 behaviour exactly: carryout, cash.
2. Card or gift card details live in **`payment_local.py` only** —
   gitignored, mode 0600, owned by the `stimpy` user, written solely by the
   interactive `set_payment.py` (masked input, Luhn + type check, last-4
   confirmation). No HTTP route, MCP tool, env var or config.py field ever
   carries a card number.
3. Every Domino's response passes through `payment.scrub()` before it is
   logged, stored in `LAST_ORDER`, or returned — `Number`, `SecurityCode`,
   `Pin`, `Expiration`, `PostalCode`, `CardType` are replaced with `***`.
4. A **pre-commit hook** (`.githooks/pre-commit`, enabled via
   `core.hooksPath`) refuses any commit whose staged diff contains a 13–19
   digit run, as a backstop against the number leaking into the public repo.
5. Delivery orders resolve the delivering store from the Domino's locator
   (or `DELIVERY_STORE_ID` in config_local.py) and add `DELIVERY_TIP` to the
   payment. The carryout store (3891) is unchanged.
6. **Gift card is the recommended non-cash option**: the same code path,
   and the blast radius is capped at the card's balance rather than a
   credit line.

## Consequences

- (+) Delivery works; no need to leave the house.
- (+) Defaults unchanged — existing `config_local.py` files and the ren
  tools keep working with no new arguments.
- (+) Card never crosses the tailnet: ren and Claude only ever say
  `pay=card`; the number stays on LXC 206.
- (-) A card number at rest in plaintext on a LAN host. Mitigated by 0600,
  the dedicated service user, systemd `ProtectSystem=strict`, and the gift
  card recommendation — not eliminated.
- (-) A mistaken `pay=card` order costs real money, unlike cash. The
  `confirm=True` gate is now the only thing between a hallucinated order
  and a charge; the ren tool docstrings say so explicitly.
- (-) Delivery price is quote + fee + tip; `/dryrun` reports `due` so the
  human approves the real total.
