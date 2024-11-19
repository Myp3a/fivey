from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from fivey.client import Client


@dataclass
class Store:
    shop_address: str
    store_city: str
    sap_code: str
    has_delivery: bool
    has_24h_delivery: bool


class StoresAPI:
    def __init__(self, cli) -> None:
        self.cli: Client = cli

    def store_by_location(self, lat: float, lon: float) -> Store:
        resp = self.cli.get(
            "/orders/v1/orders/stores/",
            params={
                "lat": lat,
                "lon": lon,
            },
        )
        assert isinstance(resp, dict)
        return Store(**resp)

    def nearby_stores_by_location(
        self, lat: float, lon: float, radius: float = 0.025
    ) -> list[Store]:
        resp = self.cli.get(
            "/cita/v1/stores/map",
            params={
                "top_latitude": lat + radius,
                "bottom_latitude": lat - radius,
                "left_longitude": lon - radius,
                "right_longitude": lon + radius,
            },
        )
        assert isinstance(resp, dict)
        res = []
        for st in resp["items"]:
            res.append(Store(st["address"], "", st["sap_code"], True, st["is_24h"]))
        return res

    def set_current_store(self, store: Store) -> Store:
        self.cli.store = store
        return store

    def get_current_store(self) -> Store | None:
        return self.cli.store
