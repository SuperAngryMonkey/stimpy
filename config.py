"""
Stimpy configuration — the entire order, hardcoded.

This is a proof-of-concept appliance: one user, one pizza, one store.
Everything that defines "the order" lives here so there's exactly one
place to change it. No env vars, no database, no abstraction. By design.
"""

# --- Store (verified against live store-locator, 2026-05-27) ---
STORE_ID = "3891"  # Domino's nearest carryout to the home address, Ft Lauderdale

# --- Customer (Domino's requires all four for a carryout order) ---
CUSTOMER_FIRST = "James"
CUSTOMER_LAST = "Smith"
CUSTOMER_EMAIL = "user@example.com"
CUSTOMER_PHONE = "5555555555"  # digits only — library strips formatting anyway

# --- Address (carryout still needs an address on the order object) ---
ADDR_STREET = "123 Redacted Street"
ADDR_CITY = "Redacted City"
ADDR_REGION = "FL"
ADDR_ZIP = "33301"

# --- The Pizza ---
# All codes read from the live menu for store 3891 on 2026-05-27.
# P12IPAZA = Medium (12") Handmade Pan Pizza (cheese base)
# Toppings are injected as Options (the library's `options=` arg is a no-op).
#   H = Ham, N = Pineapple
# Option value format: {"<side>": "<portion>"}
#   side  "1/1" = whole pizza
#   portion "1.0" = normal, "1.5" = extra, "0.5" = light
PIZZA_CODE = "P12IPAZA"
PIZZA_TOPPINGS = {
    "H": {"1/1": "1.0"},  # Ham, whole, normal
    "N": {"1/1": "1.0"},  # Pineapple, whole, normal
}
PIZZA_LABEL = "Medium Handmade Pan \u2014 Ham & Pineapple (Carryout)"

# --- Service ---
SERVICE_METHOD = "Carryout"  # library defaults to Delivery; we override
PAYMENT = "Cash"  # pay at pickup — no card data ever enters this app

# --- Runtime ---
PORT = 5000
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
