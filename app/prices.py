import requests

URL = (
    "https://api.tgju.org/v1/widget/tmp?"
    "keys=sekee,geram18,price_dollar_rl,ons,"
    "crypto-tether,crypto-bitcoin,crypto-ethereum,"
    "oil_brent,gc30"
)

NAMES = {
    "sekee": "Gold Coin",
    "geram18": "18K Gold",
    "price_dollar_rl": "Dollar",
    "ons": "Gold Ounce",
    "crypto-tether": "Tether",
    "crypto-bitcoin": "Bitcoin",
    "crypto-ethereum": "Ethereum",
    "oil_brent": "Brent Oil",
    "gc30": "Stock Index",
}


def get_prices():
    response = requests.get(URL, timeout=15)
    response.raise_for_status()

    indicators = response.json()["response"]["indicators"]
    prices = {}

    for item in indicators:
        key = item["name"]

        if key not in NAMES:
            continue

        if key in {"sekee", "geram18", "price_dollar_rl", "crypto-tether"}:
            price = item.get("p_irr", item["p"])
            unit = "T"
        elif key in {
            "crypto-bitcoin",
            "crypto-ethereum",
            "ons",
            "oil_brent",
        }:
            price = item["p"]
            unit = "$"
        else:
            price = item["p"]
            unit = ""

        try:
            if isinstance(price, float):
                price = f"{price:,.2f}"
            else:
                price = f"{int(price):,}"
        except (ValueError, TypeError):
            pass

        prices[NAMES[key]] = f"{price} {unit}".strip()

    return prices
