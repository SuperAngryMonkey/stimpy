# ADR 0002 — Carryout with cash payment

**Status:** Accepted
**Date:** 2026-05-27

## Context

Placing an order requires a payment method. Handling card data would pull a
POC into PCI-adjacent territory and create a real secret-management and
exfiltration risk on an unauthenticated app.

## Decision

Orders are Carryout, paid Cash at pickup. The payment type is hardcoded; no
card data is ever accepted, stored, or transmitted.

## Consequences

- (+) No card data anywhere — entire payment-security risk class removed.
- (+) A mistaken order costs nothing until the user chooses to collect it.
- (+) No delivery-address validation / driver dependency.
- (-) The user must physically pick up the pizza.
- (-) Delivery is not supported without a redesign and a payment review.
