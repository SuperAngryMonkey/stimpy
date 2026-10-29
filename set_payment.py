#!/usr/bin/env python3
"""
set_payment.py — the one clean way to put a card into Stimpy.

Run it ON the stimpy host, as root or the stimpy user:

    cd /opt/stimpy && sudo -u stimpy .venv/bin/python set_payment.py

It prompts (masked — nothing echoes, nothing lands in shell history),
checks the card (length, Luhn, type, MMYY, CVV, ZIP), and writes
payment_local.py with mode 0600 owned by the stimpy user. The number is
never printed; only the last four are shown for confirmation.

    set_payment.py            interactive setup
    set_payment.py --show     show what is configured (last 4 only)
    set_payment.py --clear    delete payment_local.py (back to cash only)
"""
import getpass
import os
import stat
import sys

import payment

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "payment_local.py")


def _ask(label, secret=False, default=""):
    prompt = f"{label}" + (f" [{default}]" if default else "") + ": "
    v = getpass.getpass(prompt) if secret else input(prompt)
    v = v.strip().replace(" ", "")
    return v or default


def show():
    if not os.path.exists(TARGET):
        print("No payment_local.py — Stimpy is cash-only (ADR 0002).")
        return
    print(f"Default payment : {payment.describe(payment.configured_type())}")
    print(f"Delivery tip    : ${payment.tip_amount():.2f}")
    mode = stat.S_IMODE(os.stat(TARGET).st_mode)
    print(f"File mode       : {oct(mode)}" + ("" if mode == 0o600 else "  <-- should be 0600"))


def clear():
    if os.path.exists(TARGET):
        os.remove(TARGET)
        print("payment_local.py removed. Stimpy is cash-only again.")
    else:
        print("Nothing to clear.")


def setup():
    print("Stimpy payment setup. Input is masked; nothing is echoed or logged.\n")
    choice = _ask("Default payment type (cash / card / giftcard)", default="cash").lower()
    ptype = payment.normalize(choice)
    lines = ['"""Stimpy payment secrets — gitignored, 0600, written by set_payment.py."""', ""]
    lines.append(f'PAYMENT_TYPE = "{choice}"')

    if ptype == payment.CARD:
        while True:
            number = _ask("Card number", secret=True)
            exp = _ask("Expiration (MMYY)")
            cvv = _ask("CVV", secret=True)
            zip_code = _ask("Billing ZIP")
            ok, problems = payment.validate_card(number, exp, cvv, zip_code)
            if ok:
                break
            print("  problem: " + "; ".join(problems) + "\n")
        print(f"\n  {payment.card_type(number).title()} ending {number[-4:]}, exp {exp[:2]}/{exp[2:]}")
        lines += [
            f'CARD_NUMBER = "{number}"',
            f'CARD_EXPIRATION = "{exp}"',
            f'CARD_CVV = "{cvv}"',
            f'CARD_ZIP = "{zip_code}"',
        ]
    elif ptype == payment.GIFTCARD:
        while True:
            number = _ask("Gift card number", secret=True)
            pin = _ask("Gift card PIN", secret=True)
            if number.isdigit() and pin.isdigit():
                break
            print("  problem: number and PIN must be digits\n")
        print(f"\n  Gift card ending {number[-4:]}")
        lines += [f'GIFTCARD_NUMBER = "{number}"', f'GIFTCARD_PIN = "{pin}"']

    tip = _ask("Delivery tip in dollars (used for delivery orders only)", default="3.00")
    try:
        tip = f"{float(tip):.2f}"
    except ValueError:
        tip = "0.00"
    lines.append(f'DELIVERY_TIP = "{tip}"')

    if input("\nWrite payment_local.py? [y/N] ").strip().lower() != "y":
        print("Aborted. Nothing written.")
        return

    fd = os.open(TARGET, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(TARGET, 0o600)
    print(f"Written {TARGET} (0600). Restart stimpy: systemctl restart stimpy")


if __name__ == "__main__":
    if "--show" in sys.argv:
        show()
    elif "--clear" in sys.argv:
        clear()
    else:
        try:
            setup()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted. Nothing written.")
