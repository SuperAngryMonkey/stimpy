"""
Stimpy local identity — copy to config_local.py and fill in.

config_local.py is gitignored. PII never enters the repo.
Card / gift card details do NOT go here: run set_payment.py, which
writes payment_local.py (0600) for you. See ADR 0004.
"""

CUSTOMER_FIRST = "First"
CUSTOMER_LAST = "Last"
CUSTOMER_EMAIL = "you@example.com"
CUSTOMER_PHONE = "3055551234"  # digits only

# Used as the delivery address too.
ADDR_STREET = "123 Main St"
ADDR_CITY = "Anytown"
ADDR_REGION = "FL"
ADDR_ZIP = "33301"
ADDR_TYPE = "House"  # House | Apartment | Business
ADDR_UNIT = ""  # apartment / suite number, delivery only

# Store that delivers to the address above. Leave blank to auto-resolve
# from the Domino's store locator on first delivery dry run.
DELIVERY_STORE_ID = ""
