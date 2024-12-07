from typing import TYPE_CHECKING, Any

from requests import Session, Response, exceptions

from fivey.auth import AuthAPI
from fivey.basket import BasketAPI
from fivey.catalog import CatalogAPI
from fivey.error import FiveyError
from fivey.orders import OrdersAPI, Order
from fivey.stores import StoresAPI

if TYPE_CHECKING:
    from fivey.stores import Store


class Client:
    def __init__(self) -> None:
        self.session = Session()
        self.session.verify = False
        self.base_url = "https://5d.5ka.ru/api"
        self.store: Store | None = None
        self.stores = StoresAPI(self)
        self.orders = OrdersAPI(self)
        self.catalog = CatalogAPI(self)
        self.auth = AuthAPI(self)
        self.basket = BasketAPI(self)
        self.order: Order | None = None
        self.token: str | None = None

    def _handle_api_err(self, resp: Response) -> None:
        if not resp.ok:
            errs = []
            try:
                js = resp.json()
            except exceptions.JSONDecodeError:
                e = FiveyError(
                    {
                        "http_code": resp.status_code,
                        "type": "Unknown",
                        "location": "Unknown",
                        "message": resp.text,
                    }
                )
                errs.append(e)
            else:
                if isinstance(js["detail"], list):
                    for err in js["detail"]:
                        e = FiveyError(
                            {
                                "http_code": resp.status_code,
                                "type": err.get("type", "Unknown"),
                                "location": err.get("loc", "Unknown"),
                                "message": err.get("msg", resp.status_code),
                            }
                        )
                        errs.append(e)
                else:
                    e = FiveyError(
                        {
                            "http_code": resp.status_code,
                            "type": "Unknown",
                            "location": "Unknown",
                            "message": js["detail"],
                        }
                    )
                    errs.append(e)
            raise ExceptionGroup("fivey", errs)

    def get(
        self, url: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[Any]:
        resp = self.session.get(self.base_url + url, params=params)
        self._handle_api_err(resp)
        return resp.json()

    def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        resp = self.session.post(self.base_url + url, json=json, headers=headers)
        self._handle_api_err(resp)
        return resp.json()

    def put(
        self, url: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[Any]:
        resp = self.session.put(self.base_url + url, json=json)
        self._handle_api_err(resp)
        return resp.json()

    def patch(
        self, url: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[Any]:
        resp = self.session.patch(self.base_url + url, json=json)
        self._handle_api_err(resp)
        return resp.json()

    def delete(
        self, url: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[Any]:
        resp = self.session.delete(self.base_url + url, json=json)
        self._handle_api_err(resp)
        return resp.json()
