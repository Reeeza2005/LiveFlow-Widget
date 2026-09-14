import json
import urllib.request


API_URL = "https://api.tgju.org/v1/widget/tmp?keys={}"


def get_prices(keys):
    url = API_URL.format(",".join(keys))

    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(
            response.read().decode("utf-8")
        )

    result = {}

    rial_keys = {
        "sekee",
        "geram18",
        "price_dollar_rl",
        "crypto-tether",
        "price_eur",
        "price_gbp",
    }

    for item in data["response"]["indicators"]:

        key = item["name"]

        if key in rial_keys:
            price = item.get("p_irr", item.get("p"))
        else:
            price = item.get("p")

        result[key] = {
            "price": price,
            "change": item.get("d"),
            "change_percent": item.get("dp"),
            "direction": item.get("dt"),
        }

    return result

