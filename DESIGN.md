# DESIGN — Stimpy

> *"You eediot!"* — Ren Höek, on premature abstraction

## Philosophy

Stimpy is deliberately the smallest thing that proves the point: a
self-hosted box can drive the unofficial Domino's API from order to placement.
Every temptation to generalize was resisted. One pizza, one store, one button.
"Keep what pays off, discard what doesn't" — and a POC pays off by shipping,
not by being extensible.

## Why hardcoded

The order lives entirely in `config.py`. No database, no env vars, no UI for
composing orders. Reasons:

- The user (one person) always orders the same thing.
- A single source of truth means changing the order is one file edit.
- Zero config surface = zero config bugs.

If this graduates from POC to a real tool, the natural next layer is a saved-
order store (SQLite) and a thin UI — but that's a different project. See the
ADRs.

## Why pizzapi, with patches

`pizzapi` is the de-facto Python wrapper for the API. It works but has three
quirks Stimpy works around in `order_logic.py`:

1. **No User-Agent → 403.** The library sends bare `requests` calls. Domino's
   blocks anything that doesn't look like a browser (it blocks datacenter IPs
   hardest). We monkeypatch `requests.get`/`requests.post` to inject a browser
   UA on every call. On a residential IP (the target LXC) this sails through;
   it was the single biggest reachability gotcha.
2. **Topping options are a no-op.** `add_item(options=...)` has a literal
   `# TODO: Implement item options` in the library. The default variant gives
   you a plain cheese pizza. To add ham + pineapple we inject an `Options`
   dict directly into the product after `add_item`. Format:
   `{"H": {"1/1": "1.0"}, "N": {"1/1": "1.0"}}` — topping code → side → portion.
3. **Defaults to Delivery.** `Order` sets `ServiceMethod="Delivery"`. We
   override to `Carryout` so no delivery address validation / driver is
   involved, and payment can be cash-at-pickup.

## Why cash / carryout (the defaults — see ADR 0004 for delivery + card)

Carryout + cash means the app never has to handle a card. That removes the
entire class of payment-security risk from a POC that's fundamentally about
proving API plumbing, not building a payment processor. It also means a
mistaken order costs nothing until you choose to go pick it up.

## Validate-before-place

`/order` always calls `validate()` + price before `place()`. If a product
code drifts, the store closes, or an item goes unavailable, this catches it
and returns a clean error instead of a confusing half-failure. The `/dryrun`
route is just this path with `place()` removed.

## Request flow

```
Browser  ──POST /order──>  Flask
                            │
                            ├─ build_order()      (config.py → Order object)
                            ├─ validate_order()   (Domino's validate + price)
                            └─ place_order()      (Domino's place, Cash)
                            │
Browser  <──JSON {ok, id}──┘
```
