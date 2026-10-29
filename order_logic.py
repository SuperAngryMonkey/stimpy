"""
Order logic for Stimpy.

Wraps the `pizzapi` library and works around four of its quirks:

  1. It sends bare requests with no User-Agent. Domino's 403s datacenter
     IPs without browser-like headers, so we monkeypatch requests to inject
     a UA on every call the library makes.
  2. `Order.add_item(options=...)` is a documented no-op (the library has a
     literal "TODO: Implement item options"). We inject toppings into the
     product dict manually after add_item.
  3. `Order` defaults ServiceMethod to "Delivery". We set it per order.
  4. `Menu.build_categories` raises "PRODUCT NOT FOUND" when Domino's
     Categorization tree references coupon-only product codes (e.g.
     `2XNY CouponPizza`) that don't appear in the flat menu. This kills
     menu load before our order can build. We monkeypatch the method to
     skip orphan refs instead of raising.

Payment: Cash by default (ADR 0002). Card / gift card held only in
payment_local.py and applied via payment.py (ADR 0004). Nothing in this
module ever logs or returns card fields — see payment.scrub().
"""
import logging

import requests

import config
import payment

log = logging.getLogger("stimpy.order")

# --- Quirk 1: inject a browser UA on every request the library makes ---
_orig_get = requests.get
_orig_post = requests.post


def _get(url, **kw):
    h = kw.pop("headers", {}) or {}
    h.setdefault("User-Agent", config.USER_AGENT)
    return _orig_get(url, headers=h, **kw)


def _post(url, **kw):
    h = kw.pop("headers", {}) or {}
    h.setdefault("User-Agent", config.USER_AGENT)
    return _orig_post(url, headers=h, **kw)


requests.get = _get
requests.post = _post

# Import pizzapi AFTER patching so its module-level usage picks up the patch.
from pizzapi import Address, Customer, Order, Store  # noqa: E402
from pizzapi.menu import Menu, MenuCategory  # noqa: E402


# --- Quirk 4: tolerate orphan product refs in Categorization ---
# Domino's menus include coupon-category products like `2XNY CouponPizza`
# that aren't in the flat menu_by_code. The library raises on these. We
# replace build_categories with a forgiving version that skips them.
def _build_categories_forgiving(self, category_data, parent=None):
    category = MenuCategory(category_data, parent)
    for subcategory in category_data.get("Categories", []):
        category.subcategories.append(
            _build_categories_forgiving(self, subcategory, category)
        )
    for product_code in category_data.get("Products", []):
        product = self.menu_by_code.get(product_code)
        if product is None:
            # Orphan reference (coupon-only product, etc) — skip silently.
            continue
        product.categories.append(category)
        category.products.append(product)
    return category


Menu.build_categories = _build_categories_forgiving

CARRYOUT, DELIVERY = "Carryout", "Delivery"
MODES = {"carryout": CARRYOUT, "delivery": DELIVERY}


class OrderError(Exception):
    """Raised when an order can't be built or validated."""


def normalize_mode(mode):
    m = MODES.get(str(mode or "").strip().lower())
    if mode and not m:
        raise OrderError(f"unknown mode '{mode}' (use carryout or delivery)")
    return m or config.SERVICE_METHOD


def _address():
    return Address(
        config.ADDR_STREET,
        config.ADDR_CITY,
        config.ADDR_REGION,
        config.ADDR_ZIP,
    )


def delivery_store_id():
    """The store that delivers to our address.

    config.DELIVERY_STORE_ID wins if set; otherwise ask the store locator
    for the nearest open store with Delivery service. Cached for the
    process lifetime because the answer doesn't change.
    """
    if config.DELIVERY_STORE_ID:
        return str(config.DELIVERY_STORE_ID)
    if _DELIVERY_STORE.get("id"):
        return _DELIVERY_STORE["id"]
    r = requests.get(
        "https://order.dominos.com/power/store-locator",
        params={
            "s": config.ADDR_STREET,
            "c": f"{config.ADDR_CITY}, {config.ADDR_REGION} {config.ADDR_ZIP}",
            "type": DELIVERY,
        },
        timeout=15,
    )
    r.raise_for_status()
    for s in r.json().get("Stores", []):
        if s.get("IsOnlineNow") and (s.get("ServiceIsOpen") or {}).get(DELIVERY):
            _DELIVERY_STORE["id"] = str(s["StoreID"])
            log.info("Delivery store resolved: %s", _DELIVERY_STORE["id"])
            return _DELIVERY_STORE["id"]
    raise OrderError("No Domino's store currently delivers to the configured address.")


_DELIVERY_STORE = {"id": None}


def store_for(mode):
    return delivery_store_id() if mode == DELIVERY else str(config.STORE_ID)


def build_order(coupon_code=None, mode=None):
    """Construct the canonical Stimpy order. Returns (Order, Customer).

    mode: "carryout" | "delivery" (default from config.SERVICE_METHOD).
    Optionally attaches a coupon by code. Coupon is appended to the order's
    Coupons list; whether Domino's actually applies it is determined at
    validate/price time — they'll accept-with-discount, accept-without-effect,
    or reject (Status: -1).
    """
    mode = normalize_mode(mode)
    customer = Customer(
        config.CUSTOMER_FIRST,
        config.CUSTOMER_LAST,
        config.CUSTOMER_EMAIL,
        config.CUSTOMER_PHONE,
    )
    address = _address()

    store = Store({"StoreID": store_for(mode)}, country="us")
    order = Order(store, customer, address)

    # Quirk 3: service method per order, not the library default.
    order.data["ServiceMethod"] = mode
    order.data["Address"]["Type"] = config.ADDR_TYPE
    if config.ADDR_UNIT:
        order.data["Address"]["UnitNumber"] = config.ADDR_UNIT

    # Add the pizza.
    item = order.add_item(config.PIZZA_CODE)

    # Quirk 2: inject toppings manually as Options.
    item["Options"] = dict(config.PIZZA_TOPPINGS)

    # Optionally attach a coupon. Direct dict append — library's add_coupon()
    # looks up menu.variants which doesn't contain coupon entries.
    if coupon_code:
        order.data["Coupons"].append({"Code": str(coupon_code), "Qty": 1})

    return order, customer


def validate_order(order, pay=None):
    """Validate + price the order without placing it. Returns price string.

    `pay`: "cash" | "card" | "giftcard" (default from payment_local.py, else
    cash). The matching Payments entry is attached so Domino's validates
    the shape of it too; it is never logged or returned.
    """
    if not order.validate():
        raise OrderError(
            "Domino's rejected the order at validation. "
            "Store may be closed or an item is unavailable. "
            "Check /menu?q=pan to confirm codes."
        )
    # pay_with(False) prices the order (sets Cash; we overwrite below).
    resp = order.pay_with(False)
    amount = resp.get("Order", {}).get("Amounts", {}).get("Customer")
    ptype = payment.normalize(pay) if pay else payment.configured_type()
    delivery = order.data.get("ServiceMethod") == DELIVERY
    order.data["Payments"] = [payment.build_payment(ptype, amount, delivery=delivery)]
    return amount


def total_due(order):
    """Amount + tip, for messages. Uses the Payments entry already set."""
    p = (order.data.get("Payments") or [{}])[0]
    amt = p.get("Amount")
    if amt is None:
        return order.data.get("Amounts", {}).get("Customer")
    return f"{float(amt) + float(p.get('TipAmount') or 0):.2f}"


def place_order(order):
    """Place the order for real with whatever Payments validate_order set.

    Does NOT go through pizzapi's Order.place(), which would reset Payments
    to Cash. The response is scrubbed of card fields before it is returned.
    """
    resp = order._send(order.urls.place_url(), False)  # noqa: SLF001
    return payment.scrub(resp)


def sniff_menu(query):
    """Search the live menu for the carryout store. Debug helper for /menu."""
    q = query.lower()
    r = requests.get(
        f"https://order.dominos.com/power/store/{config.STORE_ID}/menu"
        "?lang=en&structured=true",
        timeout=15,
    )
    r.raise_for_status()
    m = r.json()

    out = {"variants": [], "toppings": []}
    for code, v in m.get("Variants", {}).items():
        if q in v.get("Name", "").lower():
            out["variants"].append({"code": code, "name": v["Name"]})
    for code, t in m.get("Toppings", {}).get("Pizza", {}).items():
        if q in t.get("Name", "").lower():
            out["toppings"].append({"code": code, "name": t["Name"]})
    return out


def list_specials(service_method=CARRYOUT):
    """Return active coupons valid for the given service method at the
    store that serves that method.

    Read-only. Does not attach coupons to any order. The user reads this and
    decides whether to manually wire a coupon code into config.py.

    Returns a list of dicts: {code, name, price, methods, bundle, effective}
    sorted by price ascending (cheapest deal first).
    """
    store_id = store_for(service_method)
    r = requests.get(
        f"https://order.dominos.com/power/store/{store_id}/menu"
        "?lang=en&structured=true",
        timeout=15,
    )
    r.raise_for_status()
    m = r.json()

    out = []
    for code, v in m.get("Coupons", {}).items():
        tags = v.get("Tags", {}) or {}
        methods = tags.get("ValidServiceMethods", []) or []
        # Filter to coupons valid for our service method.
        if service_method and service_method not in methods:
            continue
        # Skip coupons with no human name — they're internal upsell stubs.
        name = (v.get("Name") or "").strip()
        if not name:
            continue
        try:
            price_f = float(v.get("Price") or 0)
        except (TypeError, ValueError):
            price_f = 0.0
        out.append({
            "code": code,
            "name": name,
            "price": v.get("Price") or "",
            "price_f": price_f,  # numeric, for sorting
            "methods": methods,
            "bundle": bool(v.get("Bundle")),
            "effective": tags.get("EffectiveOn", ""),
        })
    # Cheapest first, but push $0 entries (no advertised price) to the end.
    out.sort(key=lambda x: (x["price_f"] == 0, x["price_f"]))
    return out
