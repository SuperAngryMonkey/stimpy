# Stimpy

> *"Happy happy joy joy."* — Stimpson J. Cat

A single-purpose appliance: one web page, one button, one pizza. Press
**Feed Me** and a Medium Handmade Pan with ham and pineapple is ordered for
carryout from Domino's store #3891, paid in cash at pickup.

This is a proof of concept. It does exactly one thing, on purpose. There is
no login, no menu, no cart, no payment form — the entire order is hardcoded.
The point was to prove that a self-hosted box can drive the unofficial
Domino's ordering API end to end. It can.

---

## Claude access (ren MCP)

Claude drives stimpy through **ren** (~/Projects/ren on the Mac Studio),
a stdio MCP server exposing pizza_status / pizza_specials / pizza_dryrun /
pizza_order over the tailnet. pizza_order hard-refuses without explicit
human confirmation. See the ren README for install and registration.

## Residential IP required

**The unofficial Dominos API cannot be reached from a business, datacenter,
or cloud IP.** Dominos blocks non-residential egress outright (403s, even
with a browser User-Agent). This is why stimpy lives on an LXC on `proxlab`
behind a home connection — and why it can never move to Cloudflare Workers,
a VPS, or any hosted runtime. If requests suddenly 403, check what IP you
are egressing from before debugging anything else.

## What it does

1. Serves a single page on port 5000.
2. On **Feed Me**: builds the canonical order, validates and prices it against
   the live Domino's API, then places it for carryout with cash payment.
3. On **Dry run**: validates and prices only — never places an order. Use this
   to confirm the loop works without committing to a pizza.

## The order (hardcoded)

| Field | Value |
|---|---|
| Pizza | `P12IPAZA` — Medium (12") Handmade Pan |
| Toppings | `H` Ham (whole, normal) · `N` Pineapple (whole, normal) |
| Store | #3891 (carryout) |
| Service | Carryout |
| Payment | Cash at pickup — **no card data touches this app** |

All product/topping codes were read from the live menu for store 3891 on
2026-05-27. To change the order, edit `config.py` — it's the single source of
truth — and re-verify codes via the `/menu` route (see OPERATIONS.md).

## Quick start

```
git clone <repo> /opt/stimpy
cd /opt/stimpy
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Then hit `http://<lxc-ip>:5000`. For a permanent install see OPERATIONS.md
(systemd unit included as `stimpy.service`).

## Endpoints

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | The page with the button |
| `/order` | POST | Validate + place the order (real) |
| `/dryrun` | POST | Validate + price only (safe) |
| `/menu?q=<term>` | GET | Search live menu for codes (debug) |
| `/health` | GET | Liveness + Domino's reachability |

## Project docs

- **HANDOFF.md** — current state, what works, what's next
- **CHANGELOG.md** — version history
- **SECURITY.md** — threat model, what's exposed, payment handling
- **DESIGN.md** — why it's built this way
- **OPERATIONS.md** — deploy, run, verify, troubleshoot
- **docs/adr/** — architecture decision records

## A word of caution

The button places a real order with real consequences (a real pizza, a real
$X you owe at a real counter). The confirm dialog and the cash-at-pickup model
are the only safety rails. Don't expose this to the open internet. See
SECURITY.md.
