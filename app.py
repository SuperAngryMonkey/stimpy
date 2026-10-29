#!/usr/bin/env python3
"""
Stimpy — one-button Domino's ordering appliance.

A single page. A single button. One pizza: Medium Handmade Pan,
ham and pineapple. Carryout + cash by default; delivery and card /
gift card on request (ADR 0004).

"Happy happy joy joy." — Stimpson J. Cat
"""
import logging
import os
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request

import config
import payment
from order_logic import (
    DELIVERY,
    OrderError,
    build_order,
    list_specials,
    normalize_mode,
    place_order,
    sniff_menu,
    total_due,
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
LAST_ORDER = {"placed_at": None, "order_id": None, "amount": None, "mode": None, "pay": None}


def _params():
    """Resolve ?mode= and ?pay= (both optional) to canonical values.

    Raises OrderError / payment.PaymentError on bad input, so callers get
    a 400 before anything touches Domino's.
    """
    mode = normalize_mode(request.args.get("mode"))
    pay_arg = request.args.get("pay")
    ptype = payment.normalize(pay_arg) if pay_arg else payment.configured_type()
    return mode, ptype


def _summary(mode, ptype, due):
    how = "delivered" if mode == DELIVERY else "at pickup"
    return f"${due} {how}, {payment.describe(ptype)}"


@app.route("/")
def index():
    return render_template(
        "index.html",
        pizza_label=f"{config.PIZZA_LABEL} ({config.SERVICE_METHOD})",
        store_id=config.STORE_ID,
        last_order=LAST_ORDER,
    )


@app.route("/order", methods=["POST"])
def order():
    """Validate then place the hardcoded order.

    ?mode=carryout|delivery   default config.SERVICE_METHOD
    ?pay=cash|card|giftcard   default payment_local.PAYMENT_TYPE, else cash
    ?coupon=CODE
    """
    try:
        mode, ptype = _params()
        coupon = request.args.get("coupon") or None
        order_obj, _ = build_order(coupon_code=coupon, mode=mode)

        # Always validate before placing — catches store-closed,
        # item-unavailable, and code-drift before committing.
        price = validate_order(order_obj, pay=ptype)
        due = total_due(order_obj)
        log.info("Validation OK — mode=%s pay=%s quoted=%s due=%s", mode, ptype, price, due)

        result = place_order(order_obj)  # already scrubbed of card fields
        status = result.get("Status")
        order_id = result.get("Order", {}).get("OrderID", "unknown")
        if status == -1:
            errs = result.get("Order", {}).get("StatusItems") or result.get("StatusItems")
            raise OrderError(f"Domino's refused the order at placement: {errs}")

        LAST_ORDER.update(
            placed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            order_id=order_id,
            amount=due,
            mode=mode,
            pay=payment.describe(ptype),
        )
        log.info("ORDER PLACED — id=%s %s", order_id, _summary(mode, ptype, due))

        return jsonify(
            ok=True,
            order_id=order_id,
            amount=due,
            mode=mode,
            pay=payment.describe(ptype),
            message=f"Pizza inbound. Order {order_id}. {_summary(mode, ptype, due)}.",
        )

    except (OrderError, payment.PaymentError) as e:
        log.error("Order failed: %s", e)
        return jsonify(ok=False, message=str(e)), 400
    except requests.HTTPError as e:
        log.error("Domino's HTTP error: %s", e)
        return jsonify(ok=False, message=f"Domino's rejected the request: {e}"), 502
    except Exception as e:  # noqa: BLE001 — surface everything in the POC
        log.exception("Unexpected failure")
        return jsonify(ok=False, message=f"Unexpected: {e}"), 500


@app.route("/dryrun", methods=["GET", "POST"])
def dryrun():
    """Validate + price only. Never places. For testing the loop safely.

    Same ?mode= / ?pay= / ?coupon= as /order. With pay=card|giftcard the
    payment block is attached so Domino's validates its shape; nothing is
    charged until /order.
    """
    coupon = request.args.get("coupon") or None
    try:
        mode, ptype = _params()
        order_obj, _ = build_order(coupon_code=coupon, mode=mode)
        price = validate_order(order_obj, pay=ptype)
        due = total_due(order_obj)
        msg = f"Dry run OK. {_summary(mode, ptype, due)}"
        if coupon:
            msg += f"  (coupon {coupon} attached)"
        return jsonify(
            ok=True,
            amount=price,
            due=due,
            mode=mode,
            pay=payment.describe(ptype),
            store_id=order_obj.data.get("StoreID"),
            coupon=coupon,
            message=msg,
        )
    except Exception as e:  # noqa: BLE001
        log.exception("Dry run failed")
        return jsonify(ok=False, coupon=coupon, message=str(e)), 400


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


@app.route("/specials")
def specials():
    """Live coupons valid for ?mode=carryout|delivery at that store, cheapest first.

    Read-only. Does NOT apply coupons — they have to match an order's exact
    product configuration, and rotating coupons could silently stop matching.
    """
    try:
        mode = normalize_mode(request.args.get("mode"))
        return jsonify(mode=mode, specials=list_specials(mode))
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
        default_mode=config.SERVICE_METHOD,
        default_pay=payment.describe(payment.configured_type()),
        last_order=LAST_ORDER,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=False)
