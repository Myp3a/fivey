from typing import Any

import requests

# Найден в интернете. Работает. Пускай лежит в открытом виде
ym_api_key = "ad7c40a7-7096-43c9-b6e2-5e1f6d06b9ec"


def location_by_search(query: str) -> dict[str, Any]:
    resp = requests.get(
        "https://geocode-maps.yandex.ru/1.x/",
        params={
            "apikey": ym_api_key,
            "geocode": query,
            "format": "json",
        },
        verify=False,
    )
    data = resp.json()
    addr = data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    out = {
        "lat": float(addr["Point"]["pos"].split(" ")[1]),
        "lon": float(addr["Point"]["pos"].split(" ")[0]),
        "house": "",
        "city": "",
        "street": "",
    }
    for item in addr["metaDataProperty"]["GeocoderMetaData"]["Address"]["Components"]:
        if item["kind"] == "house":
            out["house"] = item["name"]
        if item["kind"] == "locality":
            out["city"] = item["name"]
        if item["kind"] == "area" and not out["city"]:
            out["city"] = item["name"]
        if item["kind"] == "street":
            out["street"] = item["name"]
    return out
