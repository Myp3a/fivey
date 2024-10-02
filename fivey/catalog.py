from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fivey.client import Client


@dataclass
class Item:
    plu: int
    name: str
    uom: str
    step: float
    price_regular: float
    price_discount: float | None
    quantity: float

    @property
    def price(self) -> float:
        if self.price_discount:
            return self.price_discount
        return self.price_regular


@dataclass
class Subcategory:
    id: str
    name: str


@dataclass
class Category:
    id: str
    name: str
    subcategories: list[Subcategory]


class CatalogAPI:
    def __init__(self, cli) -> None:
        self.cli: Client = cli
        self.base_path = "/catalog"

    def categories(self) -> list[Category]:
        categories: list[Category] = []
        if self.cli.store is None:
            return categories
        resp = self.cli.get(
            f"{self.base_path}/v2/stores/{self.cli.store.sap_code}/categories",
            params={"mode": "delivery"},
        )
        for cat in resp:
            assert isinstance(cat, dict)
            c = Category(
                id=cat["id"],
                name=cat["name"],
                subcategories=[
                    Subcategory(id=s["id"], name=s["name"]) for s in cat["categories"]
                ],
            )
            categories.append(c)
        return categories

    def products_list(self, category_id: str) -> list[Item]:
        if self.cli.store is None:
            return []
        resp = self.cli.get(
            f"{self.base_path}/v2/stores/{self.cli.store.sap_code}/categories/{category_id}/products_list",
            params={"mode": "delivery"},
        )
        assert isinstance(resp, dict)
        items = [
            Item(
                plu=int(i["plu"]),
                name=i["name"],
                uom=i["uom"],
                step=float(i["step"]),
                price_regular=float(i["prices"]["regular"]),
                price_discount=float(i["prices"]["discount"])
                if i["prices"]["discount"]
                else None,
                quantity=float(i["step"]),
            )
            for i in resp["products"]
        ]
        return items

    def search(self, query: str) -> list[Item]:
        if self.cli.store is None:
            return []
        resp = self.cli.get(
            f"{self.base_path}/v3/stores/{self.cli.store.sap_code}/search",
            params={
                "q": query,
                "mode": "delivery",
                "offset": 0,
                "include_restrict": False,
            },
        )
        items = []
        assert isinstance(resp, dict)
        for p in resp["products"]:
            items.append(
                Item(
                    plu=p["plu"],
                    name=p["name"],
                    uom=p["uom"],
                    step=float(p["step"]),
                    price_regular=float(p["prices"]["regular"]),
                    price_discount=float(p["prices"]["discount"])
                    if p["prices"]["discount"]
                    else None,
                    quantity=float(p["step"]),
                )
            )
        return items
