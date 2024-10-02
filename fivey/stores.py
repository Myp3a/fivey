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
        self.base_path = "/orders/v1/orders"

    def store_by_location(self, lat: float, lon: float) -> Store:
        resp = self.cli.get(
            f"{self.base_path}/stores/",
            params={
                "lat": lat,
                "lon": lon,
            },
        )
        assert isinstance(resp, dict)
        return Store(**resp)

    def set_current_store(self, store: Store) -> None:
        self.cli.store = store

    def get_current_store(self) -> Store | None:
        return self.cli.store
