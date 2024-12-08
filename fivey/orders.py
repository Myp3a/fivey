from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from fivey.catalog import Item

if TYPE_CHECKING:
    from fivey.client import Client


@dataclass
class Address:
    house: str
    street: str
    city: str


class OrderStatus(Enum):
    # WaitingForChange?
    # AdditionalPacking?
    InCart = 0
    Cancelled = 10
    Paying = 100
    Confirmed = 2
    Collecting = 3
    Packing = 6
    WaitingForCourier = 7
    Delivering = 12
    Completed = 9
    Delivered = 13


@dataclass
class Order:
    id: str
    human_id: int | None
    status: OrderStatus
    total_sum: float
    service_sum: float
    order_sum: float
    is_active: bool
    address: Address | None
    created: datetime | None
    sap_code: str
    shop_address: str
    basket: list[Item]


@dataclass
class Card:
    id: str
    number: str


class OrdersAPI:
    def __init__(self, cli) -> None:
        self.cli: Client = cli
        self.base_path = "/orders"

    def from_order_response(self, response: dict[str, Any]) -> Order:
        o = Order(
            id=response["id"],
            human_id=int(response["human_id"]) if response["human_id"] else None,
            status=OrderStatus(response["status"]),
            total_sum=float(response["total_sum"]),
            service_sum=next(
                (
                    i["amount"]
                    for i in response["basket"]["full_summary"]["subtotal"]
                    if i["name"] == "Доставка"
                ),
                0,
            )
            + next(
                (
                    i["amount"]
                    for i in response["basket"]["full_summary"]["subtotal"]
                    if i["name"] == "Сборка и упаковка"
                ),
                0,
            )
            if response.get("basket", {}).get("full_summary", False)
            else round(
                next(
                    e
                    for e in (
                        float(response["basket"]["final_sum"])
                        - float(response["basket"]["total_sum"]),
                        0,
                    )
                ),
                2,
            )
            if response.get("basket", False)
            else 0,
            order_sum=next(
                (
                    i["amount"]
                    for i in response["basket"]["full_summary"]["subtotal"]
                    if i["name"] == "Сумма заказа"
                ),
                0,
            )
            if response.get("basket", {}).get("full_summary", False)
            else next(e for e in (float(response["basket"]["total_sum"]), 0))
            if response.get("basket", False)
            else 0,
            is_active=response["is_active"],
            address=Address(
                response["address"]["house"],
                response["address"]["street"],
                response["address"]["city"],
            )
            if response["address"]
            else None,
            created=datetime.fromisoformat(response["created"])
            if response["created"]
            else None,
            sap_code=response["sap_code"],
            shop_address=response["shop_address"],
            basket=self.cli.basket.from_order(response["basket"])
            if response.get("basket", None)
            else [],
        )
        return o

    def orders(
        self, offset: int = 0, limit: int = 20, active: bool = False
    ) -> list[Order]:
        resp = self.cli.get(
            f"{self.base_path}/v3/orders/",
            params={
                "offset": offset,
                "limit": limit,
                "in_action": active,
            },
        )
        orders = []
        assert isinstance(resp, dict)
        for o in resp["items"]:
            orders.append(self.from_order_response(o))
        return orders

    def fetch_additional_data(self, order: Order) -> Order:
        resp = self.cli.get(f"{self.base_path}/v3/orders/{order.id}/")
        assert isinstance(resp, dict)
        return self.from_order_response(resp)

    def create_order(
        self, house: str, street: str, city: str, lat: str, lon: str
    ) -> Order | None:
        if self.cli.store is None:
            return None
        resp = self.cli.post(
            f"{self.base_path}/v3/orders/",
            json={
                "address": {
                    "house": house,
                    "street": street,
                    "city": city,
                    "lat": lat,
                    "lon": lon,
                },
                "is_active": True,
                "sap_code": self.cli.store.sap_code,
                "shop_address": "пиво",
                "type": "delivery",
            },
        )
        assert isinstance(resp, dict)
        o = self.from_order_response(resp)
        self.cli.order = o
        return o

    def set_address_details(
        self, entrance: str = "", flat: str = "", floor: str = "", comment: str = ""
    ) -> Order | None:
        if self.cli.order is None:
            return None
        resp = self.cli.patch(
            f"{self.base_path}/v5/orders/{self.cli.order.id}/",
            json={
                "address": {
                    "entrance": entrance,
                    "flat": flat,
                    "floor": floor,
                },
                "comment": comment,
                "delivery_type": "express",
            },
        )
        assert isinstance(resp, dict)
        return self.from_order_response(resp)

    def get_payment_methods(self) -> list[Card]:
        resp = self.cli.get(f"{self.base_path}/v1/payment-methods")
        assert isinstance(resp, dict)
        cards = [
            Card(c["id"], c["payment_name"])
            for c in resp["payments"]
            if c["type"] == "card"
        ]
        return cards

    def pay(self, payment_method: Card) -> None:
        if self.cli.order is None:
            return None
        if payment_method.id == 1:
            resp = self.cli.post(
                f"{self.base_path}/v1/orders/{self.cli.order.id}/pay-by-unlinked-card",
                json={
                    "payment_active_id": payment_method.id,
                },
                headers={"x-authorization": f"Bearer {self.cli.token}"},
            )
            assert isinstance(resp, dict)
            print(f"Оплатите заказ по ссылке: {resp["form_url"]}")
            input("После оплаты нажмите Enter")
        else:
            self.cli.post(
                f"{self.base_path}/v1/orders/{self.cli.order.id}/pay-by-linked-card",
                json={
                    "payment_active_id": payment_method.id,
                },
                headers={"x-authorization": f"Bearer {self.cli.token}"},
            )

    def revise(self) -> None:
        if self.cli.order is None:
            return None
        self.cli.post(f"{self.base_path}/v1/orders/{self.cli.order.id}/revise")

    def cancel(self, order: Order, reason: str = "Передумал") -> None:
        self.cli.post(
            f"{self.base_path}/v2/orders/{order.id}/cancel/",
            json={
                "reason_to_cancel": reason,
            },
        )
