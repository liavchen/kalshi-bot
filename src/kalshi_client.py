import base64
import os
import time
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from src.config import KALSHI_HOST, KALSHI_API_KEY_ID, KALSHI_PRIVATE_KEY_PATH
from src.logger import log

_private_key = None

def _load_private_key():
    global _private_key
    if _private_key is None:
        pem_bytes = None

        # 1. Try Streamlit secrets (cloud deploy) — handles multi-line PEM natively
        try:
            import streamlit as st
            val = st.secrets.get("KALSHI_PRIVATE_KEY", "")
            if val:
                pem_bytes = val.encode("utf-8") if val.strip().startswith("-----") \
                            else base64.b64decode(val)
        except Exception:
            pass

        # 2. Fall back to env var
        if not pem_bytes:
            pem_env = os.getenv("KALSHI_PRIVATE_KEY", "")
            if pem_env:
                pem_bytes = pem_env.encode("utf-8") if pem_env.strip().startswith("-----") \
                            else base64.b64decode(pem_env)

        # 3. Fall back to local file
        if not pem_bytes:
            with open(KALSHI_PRIVATE_KEY_PATH, "rb") as f:
                pem_bytes = f.read()

        _private_key = serialization.load_pem_private_key(
            pem_bytes, password=None, backend=default_backend()
        )
    return _private_key


def _sign(method: str, path: str, ts: str) -> str:
    msg = ts + method + path
    key = _load_private_key()
    sig = key.sign(
        msg.encode("utf-8"),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256()
    )
    return base64.b64encode(sig).decode("utf-8")


def _auth_headers(method: str, path: str) -> dict:
    ts = str(int(time.time() * 1000))
    sig = _sign(method, path, ts)
    return {
        "KALSHI-ACCESS-KEY": KALSHI_API_KEY_ID,
        "KALSHI-ACCESS-SIGNATURE": sig,
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "Content-Type": "application/json",
    }


class KalshiClient:
    def __init__(self):
        self.host = KALSHI_HOST
        self.prefix = "/trade-api/v2"
        self.session = requests.Session()

    def _get(self, path: str, params: dict = None) -> dict:
        full_path = self.prefix + path
        url = self.host + full_path
        headers = _auth_headers("GET", full_path)
        resp = self.session.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> dict:
        full_path = self.prefix + path
        url = self.host + full_path
        headers = _auth_headers("POST", full_path)
        resp = self.session.post(url, headers=headers, json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str) -> dict:
        full_path = self.prefix + path
        url = self.host + full_path
        headers = _auth_headers("DELETE", full_path)
        resp = self.session.delete(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ── Markets ──────────────────────────────────────────────────────────────

    def get_markets(self, status: str = "open", limit: int = 200, cursor: str = None) -> dict:
        params = {"status": status, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._get("/markets", params)

    def get_market(self, ticker: str) -> dict:
        return self._get(f"/markets/{ticker}")

    def get_orderbook(self, ticker: str, depth: int = 10) -> dict:
        return self._get(f"/markets/{ticker}/orderbook", {"depth": depth})

    def get_series(self, series_ticker: str) -> dict:
        return self._get(f"/series/{series_ticker}")

    # ── Portfolio ─────────────────────────────────────────────────────────────

    def get_balance(self) -> dict:
        return self._get("/portfolio/balance")

    def get_positions(self, status: str = "all") -> dict:
        return self._get("/portfolio/positions", {"status": status})

    def get_fills(self, limit: int = 50) -> dict:
        return self._get("/portfolio/fills", {"limit": limit})

    # ── Orders ────────────────────────────────────────────────────────────────

    def place_order(
        self,
        ticker: str,
        side: str,          # "yes" or "no"
        action: str,        # "buy" or "sell"
        count: int,         # number of contracts (each = $0.01 per cent of prob)
        limit_price: int,   # in cents, 1–99
        order_type: str = "limit",
        expiration_ts: int = None,
    ) -> dict:
        body = {
            "ticker": ticker,
            "side": side,
            "action": action,
            "count": count,
            "type": order_type,
            "yes_price" if side == "yes" else "no_price": limit_price,
        }
        if expiration_ts:
            body["expiration_ts"] = expiration_ts
        log.info(f"Placing order: {ticker} {action} {count}x {side} @ {limit_price}¢")
        return self._post("/portfolio/orders", body)

    def cancel_order(self, order_id: str) -> dict:
        log.info(f"Cancelling order {order_id}")
        return self._delete(f"/portfolio/orders/{order_id}")

    def get_orders(self, status: str = "resting") -> dict:
        return self._get("/portfolio/orders", {"status": status})
