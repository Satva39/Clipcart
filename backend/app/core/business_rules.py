from decimal import Decimal, ROUND_HALF_UP

DEFAULT_MARKETING_FEE = Decimal("2.00")
DEFAULT_SUPPLIER_REGISTRATION_FEE = Decimal("50.00")
DEFAULT_TAX_RATE = Decimal("0.18")
DEFAULT_TAX_THRESHOLD = Decimal("2000.00")
DEFAULT_TAX_CAP = Decimal("500.00")


def money(value):
    return Decimal(str(value or "0")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _setting_decimal(key, fallback):
    try:
        from app.modules.admin.services import PlatformSettingsService

        return money(PlatformSettingsService.get_decimal(key))
    except Exception:
        return money(fallback)


def get_marketing_fee():
    return _setting_decimal("marketing_fee", DEFAULT_MARKETING_FEE)


def get_supplier_registration_fee():
    return _setting_decimal(
        "supplier_registration_fee",
        DEFAULT_SUPPLIER_REGISTRATION_FEE,
    )


def get_tax_rate():
    try:
        from app.modules.admin.services import PlatformSettingsService

        return Decimal(str(PlatformSettingsService.get("tax_rate", DEFAULT_TAX_RATE)))
    except Exception:
        return DEFAULT_TAX_RATE


def get_tax_threshold():
    return _setting_decimal("tax_threshold", DEFAULT_TAX_THRESHOLD)


def get_tax_cap():
    return _setting_decimal("tax_cap", DEFAULT_TAX_CAP)


def tax_for(base):
    base = money(base)
    if base <= get_tax_threshold():
        return Decimal("0.00")
    tax = money(base * get_tax_rate())
    return min(tax, get_tax_cap())


def calculate_platform_charges(taxable_amount):
    charges = checkout_charges(taxable_amount, Decimal("0.00"))
    return charges


def checkout_charges(subtotal, discount):
    taxable_base = money(max(Decimal("0.00"), money(subtotal) - money(discount)))
    tax = tax_for(taxable_base)
    marketing_fee = get_marketing_fee()
    return {
        "taxable_base": taxable_base,
        "marketing_fee": marketing_fee,
        "tax": tax,
        "total_platform_charges": money(marketing_fee + tax),
    }
