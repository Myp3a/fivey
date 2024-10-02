from typing import TYPE_CHECKING, Any

from fivey.catalog import Item
from fivey.orders import Order

if TYPE_CHECKING:
    from fivey.client import Client


class BasketAPI:
    def __init__(self, cli) -> None:
        self.cli: Client = cli
        self.base_path = "/orders/v3/orders"

    def put(self, item: Item) -> Order | None:
        if self.cli.order is None:
            return None
        if basket_item := next(
            (i for i in self.cli.order.basket if item.plu == i.plu), None
        ):
            quantity = item.quantity + basket_item.quantity
            resp = self.cli.put(
                f"{self.base_path}/{self.cli.order.id}/item/{item.plu}/",
                json={
                    "plu": item.plu,
                    "qty": quantity,
                    "uom": item.uom,
                },
            )
        else:
            resp = self.cli.post(
                f"{self.base_path}/{self.cli.order.id}/item/",
                json={
                    "plu": item.plu,
                    "qty": item.quantity,
                    "uom": item.uom,
                },
            )
        assert isinstance(resp, dict)
        o = self.cli.orders.from_order_response(resp)
        self.cli.order = o
        return o

    def remove(self, item: Item) -> Order | None:
        if self.cli.order is None:
            return None
        if any([item.plu == i.plu for i in self.cli.order.basket]):
            resp = self.cli.delete(
                f"{self.base_path}/{self.cli.order.id}/item/{item.plu}/"
            )
        assert isinstance(resp, dict)
        o = self.cli.orders.from_order_response(resp)
        self.cli.order = o
        return o

    def from_order(self, order_basket: dict[str, Any]) -> list[Item]:
        items = []
        for i in order_basket["items"]:
            i_obj = Item(
                plu=int(i["product_plu"]),
                name=i["name"],
                uom=i["uom"],
                step=float(i["step"]),
                price_regular=float(i["price_reg"]),
                price_discount=float(i["price_promo"]) if i["price_promo"] else None,
                quantity=float(i["quantity"]),
            )
            items.append(i_obj)
        return items
