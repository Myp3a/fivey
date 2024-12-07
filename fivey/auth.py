import base64
import hashlib
import json
import os
import random
import re
import string
from typing import TYPE_CHECKING
import uuid

import requests
from playwright import sync_api

if TYPE_CHECKING:
    from fivey.client import Client


class AuthAPI:
    def __init__(self, cli) -> None:
        self.cli: Client = cli

    def check_auth(self, token: str) -> bool:
        resp = requests.get(
            "https://gw-el5.x5.ru/api/profile/v1/user",
            headers={"Authorization": f"Bearer {token}"},
            verify=False,
        )
        if resp.ok:
            return True
        return False

    def load_token_from_file(self) -> bool:
        if os.path.isfile(".token"):
            with open(".token", "r", encoding="utf-8") as inf:
                try:
                    auth_data = json.loads(inf.read())
                    token = auth_data["access_token"]
                    refresh_token = auth_data["refresh_token"]
                except (json.JSONDecodeError, KeyError):
                    return False
            if self.check_auth(token):
                self.set_token(token, refresh_token)
                return True
            auth_data = self.fetch_refresh_token(refresh_token)
            token = auth_data["access_token"]
            refresh_token = auth_data["refresh_token"]
            if self.check_auth(token):
                self.set_token(token, refresh_token)
                return True
        return False

    def set_token(self, token: str, refresh_token: str) -> bool:
        if self.check_auth(token):
            self.cli.token = token
            self.cli.session.headers.update(
                {
                    "x-authorization": f"Bearer {token}",
                    "x-device-id": uuid.UUID(
                        "".join(random.choices(string.hexdigits, k=32))
                    ).hex,
                    "x-package-name": "ru.pyaterochka.app.browser",
                    "x-app-version": "3.5.0",
                    "x-platform": "android",
                }
            )
            with open(".token", "w", encoding="utf-8") as outf:
                outf.write(
                    json.dumps({"access_token": token, "refresh_token": refresh_token})
                )
            return True
        return False

    def fetch_refresh_token(self, refresh_token: str) -> dict[str, str]:
        resp = self.cli.session.post(
            "https://id.x5.ru/auth/realms/ssox5id/protocol/openid-connect/token",
            data={
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
                "client_id": "tc5_mob",
            },
        )
        data = resp.json()
        token = data["access_token"]
        refresh_token = data["refresh_token"]
        return {"access_token": token, "refresh_token": refresh_token}

    def interactive_auth(self, phone: str) -> bool:
        with sync_api.sync_playwright() as pw:
            browser = pw.chromium.launch()
            code_verifier = "".join(
                random.choices(string.ascii_letters + string.digits, k=128)
            )
            code_sha_256 = hashlib.sha256(code_verifier.encode("utf-8")).digest()
            b64 = base64.urlsafe_b64encode(code_sha_256)
            code_challenge = b64.decode("utf-8").replace("=", "")
            page = browser.new_page()
            page.goto(
                "https://id.x5.ru/auth/realms/ssox5id/protocol/openid-connect/auth"
                "?redirect_uri=ru.pyaterochka.app.browser://oauth2redirect"
                "&client_id=tc5_mob"
                "&response_type=code"
                "&scope=profile offline_access"
                "&response_mode=query"
                f"&code_challenge={code_challenge}"
                "&code_challenge_method=S256"
                f"&device_id={''.join(random.choices(string.ascii_letters + string.digits, k=128))}"
                f"&state={''.join(random.choices(string.ascii_letters + string.digits, k=22))}"
                f"&nonce={''.join(random.choices(string.ascii_letters + string.digits, k=22))}"
            )
            page.get_by_role("textbox").fill(phone)
            page.get_by_role("button").filter(has_text="Подтвердить вход").click()

            code = input("Код: ")

            page.wait_for_load_state("load")
            with page.expect_request(lambda u: "oauth2redirect" in u.url) as resp:
                for sym in code:
                    page.keyboard.press(sym)
                token_url = resp.value.url
            if "yandex" in token_url:
                # Плохая практика, нужно найти другой способ определения успешности кода
                return False
            _, code = token_url.split("&code=")
            resp = self.cli.session.post(
                "https://id.x5.ru/auth/realms/ssox5id/protocol/openid-connect/token",
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": "ru.pyaterochka.app.browser://oauth2redirect",
                    "code_verifier": code_verifier,
                    "client_id": "tc5_mob",
                },
            )
            data = resp.json()
            token = data["access_token"]
            refresh_token = data["refresh_token"]
            self.set_token(token, refresh_token)
            return True

    def _ask_for_sms_code_cli(self, phone: str) -> None:
        """Не работает. Возвращает ошибку авторизации. Будет доделано в будущем."""
        code_verifier = "".join(
            random.choices(string.ascii_letters + string.digits, k=128)
        )
        code_sha_256 = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        b64 = base64.urlsafe_b64encode(code_sha_256)
        code_challenge = b64.decode("utf-8").replace("=", "")
        resp = self.cli.session.get(
            "https://id.x5.ru/auth/realms/ssox5id/protocol/openid-connect/auth",
            params={
                "redirect_uri": "ru.pyaterochka.app.browser://oauth2redirect",
                "client_id": "tc5_mob",
                "response_type": "code",
                "scope": "profile offline_access",
                "response_mode": "query",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "device_id": "".join(
                    random.choices(string.ascii_letters + string.digits, k=128)
                ),
                "state": "".join(
                    random.choices(string.ascii_letters + string.digits, k=22)
                ),
                "nonce": "".join(
                    random.choices(string.ascii_letters + string.digits, k=22)
                ),
            },
        )
        html = resp.text
        print(html)
        auth_url = re.findall(
            r'(?:<form id="kc-form-login")(?:.*?)(https://id.x5.ru/auth/realms/ssox5id/login-actions/authenticate.*?)(?:" method="post">)',
            html,
        )[0].replace("&amp;", "&")
        resp = self.cli.session.post(
            auth_url,
            data={
                "username": phone,
                "rememberMe": "on",
            },
        )
        print(resp.text)
