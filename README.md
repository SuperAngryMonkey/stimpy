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

## Runtime

Registered in Claude Desktop (claude_desktop_config.json) pointing at
.venv/bin/python server.py with STIMPY_URL in env.
