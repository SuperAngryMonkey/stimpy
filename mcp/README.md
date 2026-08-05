# ren

> "It is not I who am crazy. It is I who am MAD!" — Ren Hoek

The mouth to stimpy's hands. A stdio MCP server that lets Claude check,
price, and — with explicit human confirmation — place the standing
Dominos carryout order via the stimpy appliance (LXC 206) over the
tailnet.

## Tools

| Tool | Effect |
|---|---|
| pizza_status | Liveness + Dominos reachability + last order |
| pizza_specials | Live carryout coupons, read-only |
| pizza_dryrun(coupon) | Validate + price, never places |
| pizza_order(confirm, coupon) | Places the real order; hard-refuses without confirm=True |

## Safety

pizza_order follows the christian contract: confirm=True is only ever
set after the human explicitly approves that specific order. Payment is
cash at pickup — no card data exists anywhere in ren or stimpy.

## Residential IP required

Ren itself runs anywhere on the tailnet, but stimpy — the box that
actually talks to Dominos — must egress from a residential IP. Dominos
blocks business, datacenter, and cloud IPs outright. Do not relocate
stimpy to hosted infrastructure; ren will start returning 403s through
no fault of its own.

## Install

Requires Homebrew Python 3.10+ (built against 3.14). The mcp package is
pinned <2 — mcp 2.0 moved FastMCP and breaks the import.

```
cd ~/Projects/stimpy/mcp
/opt/homebrew/bin/python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Claude Desktop registration

Add to ~/Library/Application Support/Claude/claude_desktop_config.json
under mcpServers, then fully quit (Cmd-Q) and relaunch Claude Desktop:

```json
"ren": {
  "command": "/Users/jamessmith/Projects/stimpy/mcp/.venv/bin/python",
  "args": ["/Users/jamessmith/Projects/stimpy/mcp/server.py"],
  "env": { "STIMPY_URL": "http://100.84.231.64:5000" }
}
```

STIMPY_URL points at the stimpy LXC over the tailnet; change it if the
appliance moves (residential egress only — see above).

## Usage flow

1. pizza_status — confirm stimpy is up and Dominos is reachable
2. pizza_specials — see live carryout coupons
3. pizza_dryrun(coupon) — price the order without placing it
4. pizza_order(confirm=True, coupon) — place it, only after the human
   explicitly says go. Cash at pickup.

Verified 2026-08-05: rack $16.04, coupon 9204 → $10.69.
