"""Shared constants for ECB Data Portal assets."""

# Asset group name for all ECB assets
ASSET_GROUP = "ecb"

# Currencies to collect from ECB
# Organized by Illy business relevance
ECB_CURRENCIES = [
    # Major markets
    "USD",
    "GBP",
    "JPY",
    "CHF",
    "AUD",
    "CAD",
    "NZD",
    # Coffee/Cocoa sourcing (Brazil, Indonesia, India, Mexico, Colombia)
    "BRL",
    "IDR",
    "INR",
    "MXN",
    # Tea sourcing (China, South Korea, Thailand, Malaysia, Singapore, Hong Kong)
    "CNY",
    "KRW",
    "THB",
    "MYR",
    "SGD",
    "HKD",
    # Europe (non-EUR)
    "SEK",
    "NOK",
    "DKK",
    "PLN",
    "CZK",
    "HUF",
    "RON",
    "BGN",
    # Other relevant markets
    "ZAR",
    "TRY",
    "RUB",
    "ILS",
]

__all__ = [
    "ASSET_GROUP",
    "ECB_CURRENCIES",
]
