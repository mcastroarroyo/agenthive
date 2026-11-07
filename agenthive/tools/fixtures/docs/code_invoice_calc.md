# Code Review Sample — invoice_calc.py (billing export) with failing tests

**Repository:** billing-export (synthetic example) · **Ticket:** BILL-412 · **Reported by:** Finance Systems, 2026-11-03

> Finance reports two problems in the November invoice run: some invoice totals are **one cent lower** than the
> amount Finance calculates by hand, and invoices with a **discount show more tax** than expected. CI is red:
> `test_invoice_calc.py` has failing tests. The business rules the code must follow are in the module docstring
> (Finance policy FIN-07).

## invoice_calc.py

```python
"""invoice_calc - invoice totals for the billing export (owner: Finance Systems).

Business rules (Finance policy FIN-07):
  R1. Money is rounded to whole cents, half up: 2.675 -> 2.68 and 0.125 -> 0.13.
  R2. A percentage discount applies to the pre-tax subtotal; tax is charged
      on the discounted subtotal.
  R3. Tax rates by category: standard 8.25 %, reduced 4 %, exempt 0 %.
  R4. Quantities are positive integers; unit prices are non-negative.
"""

TAX_RATES = {"standard": 0.0825, "reduced": 0.04, "exempt": 0.0}


def round_money(amount):
    """Round a money amount to whole cents (R1)."""
    return round(amount, 2)


def line_total(unit_price, quantity):
    """Price x quantity for one invoice line, validated (R4)."""
    if not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("quantity must be a positive integer")
    if unit_price < 0:
        raise ValueError("unit_price must be non-negative")
    return unit_price * quantity


def invoice_totals(lines, tax_category="standard", discount_pct=0):
    """Return subtotal, discount, tax and total for a list of invoice lines.

    lines: list of {"sku": str, "unit_price": number, "quantity": int}
    """
    if tax_category not in TAX_RATES:
        raise ValueError(f"unknown tax category: {tax_category}")
    if not 0 <= discount_pct <= 100:
        raise ValueError("discount_pct must be between 0 and 100")
    if not lines:
        raise ValueError("an invoice needs at least one line")

    subtotal = sum(line_total(l["unit_price"], l["quantity"]) for l in lines)
    tax = subtotal * TAX_RATES[tax_category]
    discount = (subtotal + tax) * discount_pct / 100
    total = subtotal + tax - discount

    return {
        "subtotal": round_money(subtotal),
        "discount": round_money(discount),
        "tax": round_money(tax),
        "total": round_money(total),
    }


def format_invoice(customer, lines, **options):
    """One-line summary used in the billing e-mail."""
    t = invoice_totals(lines, **options)
    return f"{customer}: {len(lines)} line(s), total ${t['total']:.2f} (tax ${t['tax']:.2f})"
```

## test_invoice_calc.py

```python
import unittest
from decimal import Decimal

from invoice_calc import format_invoice, invoice_totals, line_total, round_money


def money(x):
    """Compare money by its decimal value (works for float and Decimal results)."""
    return Decimal(str(x))


class InvoiceCalcTests(unittest.TestCase):

    def test_round_half_up(self):
        self.assertEqual(money(round_money(2.675)), Decimal("2.68"))
        self.assertEqual(money(round_money(0.125)), Decimal("0.13"))

    def test_standard_tax_simple(self):
        r = invoice_totals([{"sku": "SVC-1", "unit_price": 10.00, "quantity": 3}])
        self.assertEqual(money(r["subtotal"]), Decimal("30.00"))
        self.assertEqual(money(r["tax"]), Decimal("2.48"))
        self.assertEqual(money(r["total"]), Decimal("32.48"))

    def test_standard_tax_half_cent(self):
        # 8.25 % of 50.00 = 4.125 -> 4.13 (R1)
        r = invoice_totals([{"sku": "LIC-2", "unit_price": 12.50, "quantity": 4}])
        self.assertEqual(money(r["subtotal"]), Decimal("50.00"))
        self.assertEqual(money(r["tax"]), Decimal("4.13"))
        self.assertEqual(money(r["total"]), Decimal("54.13"))

    def test_discount_applies_before_tax(self):
        # R2: 25 % off 200.00 = 50.00; 4 % tax on 150.00 = 6.00
        r = invoice_totals([{"sku": "HW-9", "unit_price": 200.00, "quantity": 1}],
                           tax_category="reduced", discount_pct=25)
        self.assertEqual(money(r["discount"]), Decimal("50.00"))
        self.assertEqual(money(r["tax"]), Decimal("6.00"))
        self.assertEqual(money(r["total"]), Decimal("156.00"))

    def test_discount_and_rounding_together(self):
        # 20 % off 62.50 = 12.50; 8.25 % of 50.00 = 4.125 -> 4.13
        r = invoice_totals([{"sku": "SVC-7", "unit_price": 62.50, "quantity": 1}], discount_pct=20)
        self.assertEqual(money(r["discount"]), Decimal("12.50"))
        self.assertEqual(money(r["tax"]), Decimal("4.13"))
        self.assertEqual(money(r["total"]), Decimal("54.13"))

    def test_exempt_multi_line(self):
        r = invoice_totals([{"sku": "A-1", "unit_price": 19.99, "quantity": 3},
                            {"sku": "B-2", "unit_price": 5.01, "quantity": 2}], tax_category="exempt")
        self.assertEqual(money(r["subtotal"]), Decimal("69.99"))
        self.assertEqual(money(r["tax"]), Decimal("0"))
        self.assertEqual(money(r["total"]), Decimal("69.99"))

    def test_rejects_bad_quantity(self):
        with self.assertRaises(ValueError):
            line_total(5.00, 0)
        with self.assertRaises(ValueError):
            line_total(5.00, 1.5)

    def test_rejects_unknown_tax_category(self):
        with self.assertRaises(ValueError):
            invoice_totals([{"sku": "A-1", "unit_price": 1.00, "quantity": 1}], tax_category="luxury")

    def test_rejects_discount_over_100(self):
        with self.assertRaises(ValueError):
            invoice_totals([{"sku": "A-1", "unit_price": 1.00, "quantity": 1}], discount_pct=120)

    def test_format_invoice(self):
        s = format_invoice("Acme Field Services", [{"sku": "SVC-1", "unit_price": 10.00, "quantity": 3}])
        self.assertEqual(s, "Acme Field Services: 1 line(s), total $32.48 (tax $2.48)")


if __name__ == "__main__":
    unittest.main()
```

## Run module and tests together

The block below is the module and the tests concatenated into one self-contained script (no imports between
files), so it can be executed as-is in a code-execution sandbox. It prints the unittest report to stdout.

```python
"""invoice_calc - invoice totals for the billing export (owner: Finance Systems).

Business rules (Finance policy FIN-07):
  R1. Money is rounded to whole cents, half up: 2.675 -> 2.68 and 0.125 -> 0.13.
  R2. A percentage discount applies to the pre-tax subtotal; tax is charged
      on the discounted subtotal.
  R3. Tax rates by category: standard 8.25 %, reduced 4 %, exempt 0 %.
  R4. Quantities are positive integers; unit prices are non-negative.
"""

TAX_RATES = {"standard": 0.0825, "reduced": 0.04, "exempt": 0.0}


def round_money(amount):
    """Round a money amount to whole cents (R1)."""
    return round(amount, 2)


def line_total(unit_price, quantity):
    """Price x quantity for one invoice line, validated (R4)."""
    if not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("quantity must be a positive integer")
    if unit_price < 0:
        raise ValueError("unit_price must be non-negative")
    return unit_price * quantity


def invoice_totals(lines, tax_category="standard", discount_pct=0):
    """Return subtotal, discount, tax and total for a list of invoice lines.

    lines: list of {"sku": str, "unit_price": number, "quantity": int}
    """
    if tax_category not in TAX_RATES:
        raise ValueError(f"unknown tax category: {tax_category}")
    if not 0 <= discount_pct <= 100:
        raise ValueError("discount_pct must be between 0 and 100")
    if not lines:
        raise ValueError("an invoice needs at least one line")

    subtotal = sum(line_total(l["unit_price"], l["quantity"]) for l in lines)
    tax = subtotal * TAX_RATES[tax_category]
    discount = (subtotal + tax) * discount_pct / 100
    total = subtotal + tax - discount

    return {
        "subtotal": round_money(subtotal),
        "discount": round_money(discount),
        "tax": round_money(tax),
        "total": round_money(total),
    }


def format_invoice(customer, lines, **options):
    """One-line summary used in the billing e-mail."""
    t = invoice_totals(lines, **options)
    return f"{customer}: {len(lines)} line(s), total ${t['total']:.2f} (tax ${t['tax']:.2f})"


import unittest
from decimal import Decimal


def money(x):
    """Compare money by its decimal value (works for float and Decimal results)."""
    return Decimal(str(x))


class InvoiceCalcTests(unittest.TestCase):

    def test_round_half_up(self):
        self.assertEqual(money(round_money(2.675)), Decimal("2.68"))
        self.assertEqual(money(round_money(0.125)), Decimal("0.13"))

    def test_standard_tax_simple(self):
        r = invoice_totals([{"sku": "SVC-1", "unit_price": 10.00, "quantity": 3}])
        self.assertEqual(money(r["subtotal"]), Decimal("30.00"))
        self.assertEqual(money(r["tax"]), Decimal("2.48"))
        self.assertEqual(money(r["total"]), Decimal("32.48"))

    def test_standard_tax_half_cent(self):
        # 8.25 % of 50.00 = 4.125 -> 4.13 (R1)
        r = invoice_totals([{"sku": "LIC-2", "unit_price": 12.50, "quantity": 4}])
        self.assertEqual(money(r["subtotal"]), Decimal("50.00"))
        self.assertEqual(money(r["tax"]), Decimal("4.13"))
        self.assertEqual(money(r["total"]), Decimal("54.13"))

    def test_discount_applies_before_tax(self):
        # R2: 25 % off 200.00 = 50.00; 4 % tax on 150.00 = 6.00
        r = invoice_totals([{"sku": "HW-9", "unit_price": 200.00, "quantity": 1}],
                           tax_category="reduced", discount_pct=25)
        self.assertEqual(money(r["discount"]), Decimal("50.00"))
        self.assertEqual(money(r["tax"]), Decimal("6.00"))
        self.assertEqual(money(r["total"]), Decimal("156.00"))

    def test_discount_and_rounding_together(self):
        # 20 % off 62.50 = 12.50; 8.25 % of 50.00 = 4.125 -> 4.13
        r = invoice_totals([{"sku": "SVC-7", "unit_price": 62.50, "quantity": 1}], discount_pct=20)
        self.assertEqual(money(r["discount"]), Decimal("12.50"))
        self.assertEqual(money(r["tax"]), Decimal("4.13"))
        self.assertEqual(money(r["total"]), Decimal("54.13"))

    def test_exempt_multi_line(self):
        r = invoice_totals([{"sku": "A-1", "unit_price": 19.99, "quantity": 3},
                            {"sku": "B-2", "unit_price": 5.01, "quantity": 2}], tax_category="exempt")
        self.assertEqual(money(r["subtotal"]), Decimal("69.99"))
        self.assertEqual(money(r["tax"]), Decimal("0"))
        self.assertEqual(money(r["total"]), Decimal("69.99"))

    def test_rejects_bad_quantity(self):
        with self.assertRaises(ValueError):
            line_total(5.00, 0)
        with self.assertRaises(ValueError):
            line_total(5.00, 1.5)

    def test_rejects_unknown_tax_category(self):
        with self.assertRaises(ValueError):
            invoice_totals([{"sku": "A-1", "unit_price": 1.00, "quantity": 1}], tax_category="luxury")

    def test_rejects_discount_over_100(self):
        with self.assertRaises(ValueError):
            invoice_totals([{"sku": "A-1", "unit_price": 1.00, "quantity": 1}], discount_pct=120)

    def test_format_invoice(self):
        s = format_invoice("Acme Field Services", [{"sku": "SVC-1", "unit_price": 10.00, "quantity": 3}])
        self.assertEqual(s, "Acme Field Services: 1 line(s), total $32.48 (tax $2.48)")


import sys
unittest.main(argv=["x"], exit=False, verbosity=2,
              testRunner=unittest.TextTestRunner(stream=sys.stdout, verbosity=2))
```
