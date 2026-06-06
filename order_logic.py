"""
Order logic for Stimpy.

Wraps the `pizzapi` library and works around four of its quirks:

  1. It sends bare requests with no User-Agent. Domino's 403s datacenter
     IPs without browser-like headers, so we monkeypatch requests to inject
     a UA on every call the library makes.
  2. `Order.add_item(options=...)` is a documented no-op (the library has a
     literal "TODO: Implement item options"). We inject toppings into the
     product dict manually after add_item.
  3. `Order` defaults ServiceMethod to "Delivery". We force "Carryout".
  4. `Menu.build_categories` raises "PRODUCT NOT FOUND" when Domino's
     Categorization tree references coupon-only product codes (e.g.
     `2XNY CouponPizza`) that don't appear in the flat menu. This kills
     menu load before our order can build. We monkeypatch the method to
     skip orphan refs instead of raising.

Nothing here ever handles card data. Payment is Cash / pay-at-pickup.
"""
import requests

import config

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


class OrderError(Exception):
    """Raised when an order can't be built or validated."""


def _store():
    return Store({"StoreID": config.STORE_ID}, country="us")


def build_order():
    """Construct the canonical Stimpy order. Returns (Order, Customer)."""
    customer = Customer(
        config.CUSTOMER_FIRST,
        config.CUSTOMER_LAST,
        config.CUSTOMER_EMAIL,
        config.CUSTOMER_PHONE,
    )
    address = Address(
        config.ADDR_STREET,
        config.ADDR_CITY,
        config.ADDR_REGION,
        config.ADDR_ZIP,
    )

    store = _store()
    order = Order(store, customer, address)

    # Quirk 3: this is a carryout order.
    order.data["ServiceMethod"] = config.SERVICE_METHOD
    order.data["Address"]["Type"] = "House"

    # Add the pizza.
    item = order.add_item(config.PIZZA_CODE)

    # Quirk 2: inject toppings manually as Options.
    item["Options"] = dict(config.PIZZA_TOPPINGS)

    return order, customer


def validate_order(order):
    """Validate + price the order without placing it. Returns price string."""
    if not order.validate():
        raise OrderError(
            "Domino's rejected the order at validation. "
            "Store may be closed or an item is unavailable. "
            "Check /menu?q=pan to confirm codes."
        )
    # pay_with(False) prices the order and sets Cash payment.
    resp = order.pay_with(False)
    amount = resp.get("Order", {}).get("Amounts", {}).get("Customer")
    return amount


def place_order(order):
    """Place the order for real. Cash payment, pay at pickup."""
    return order.place(card=False)


def sniff_menu(query):
    """Search the live menu for store 3891. Debug helper for /menu route."""
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
