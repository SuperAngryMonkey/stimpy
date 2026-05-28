#!/usr/bin/env python3
"""
Stimpy — one-button Domino's carryout ordering appliance.

A single page. A single button. One pizza: Medium Handmade Pan,
ham and pineapple, carryout from store 3891, pay at pickup.

"Happy happy joy joy." — Stimpson J. Cat
"""
import logging
import os
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request

import config
from order_logic import (
    OrderError,
    build_order,
    place_order,
    sniff_menu,
    validate_order,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("stimpy")

app = Flask(__name__)

# In-memory record of the last order placed this process lifetime.
# Persistence is deliberately out of scope for the POC (see DESIGN.md).
LAST_ORDER = {"placed_at": None, "order_id": None, "amount": None}


@app.route("/")
def index():
    return render_template(
        "index.html",
        pizza_label=config.PIZZA_LABEL,
        store_id=config.STORE_ID,
        last_order=LAST_ORDER,
    )


@app.route("/order", methods=["POST"])
def order():
    """Validate then place the hardcoded order. Cash / pay-at-pickup."""
    try:
        order_obj, customer = build_order()

        # Always validate before placing — catches store-closed,
        # item-unavailable, and code-drift before committing.
        price = validate_order(order_obj)
        log.info("Validation OK — quoted amount: %s", price)

        result = place_order(order_obj)
        order_id = result.get("Order", {}).get("OrderID", "unknown")

        LAST_ORDER.update(
            placed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            order_id=order_id,
            amount=price,
        )
        log.info("ORDER PLACED — id=%s amount=%s", order_id, price)

        return jsonify(
            ok=True,
            order_id=order_id,
            amount=price,
            message=f"Pizza inbound. Order {order_id}. ${price} at pickup.",
        )

    except OrderError as e:
        log.error("Order failed: %s", e)
        return jsonify(ok=False, message=str(e)), 400
    except requests.HTTPError as e:
        log.error("Domino's HTTP error: %s", e)
        return jsonify(ok=False, message=f"Domino's rejected the request: {e}"), 502
    except Exception as e:  # noqa: BLE001 — surface everything in the POC
        log.exception("Unexpected failure")
        return jsonify(ok=False, message=f"Unexpected: {e}"), 500


@app.route("/dryrun", methods=["POST"])
def dryrun():
    """Validate + price only. Never places. For testing the loop safely."""
    try:
        order_obj, _ = build_order()
        price = validate_order(order_obj)
        return jsonify(ok=True, amount=price, message=f"Dry run OK. Quote: ${price}")
    except Exception as e:  # noqa: BLE001
        log.exception("Dry run failed")
        return jsonify(ok=False, message=str(e)), 400


@app.route("/menu")
def menu():
    """Debug route: search the live menu for product/topping codes.

    Usage: /menu?q=pan   or   /menu?q=ham
    Lets you re-verify codes from the box that actually places orders,
    without leaving the LXC. See OPERATIONS.md.
    """
    q = request.args.get("q", "").lower()
    if not q:
        return jsonify(error="pass ?q=<search term>"), 400
    try:
        return jsonify(sniff_menu(q))
    except Exception as e:  # noqa: BLE001
        return jsonify(error=str(e)), 502


@app.route("/health")
def health():
    """Liveness + Domino's reachability check."""
    try:
        r = requests.get(
            f"https://order.dominos.com/power/store/{config.STORE_ID}/profile",
            headers={"User-Agent": config.USER_AGENT},
            timeout=10,
        )
        reachable = r.status_code == 200
    except Exception:  # noqa: BLE001
        reachable = False
    return jsonify(
        ok=True,
        dominos_reachable=reachable,
        store_id=config.STORE_ID,
        last_order=LAST_ORDER,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=False)
