from src.kalshi_client import KalshiClient
from src.risk import RiskManager
from src.strategy import Signal
from src.logger import log


class Executor:
    def __init__(self, risk: RiskManager, dry_run: bool = True):
        self.kalshi = KalshiClient()
        self.risk = risk
        self.dry_run = dry_run
        if dry_run:
            log.warning("DRY RUN mode — no real orders will be placed")

    def execute_signals(self, signals: list[Signal]):
        if self.risk.is_killed:
            log.error("Bot is killed — skipping execution")
            return

        balance_usd = self._get_balance()
        log.info(f"Current balance: ${balance_usd:.2f}")

        for sig in signals:
            self._execute_one(sig, balance_usd)

    def _get_balance(self) -> float:
        try:
            data = self.kalshi.get_balance()
            # balance field is in cents
            return data.get("balance", 0) / 100
        except Exception as e:
            log.error(f"Failed to fetch balance: {e}")
            return 0.0

    def _execute_one(self, sig: Signal, balance_usd: float):
        price_cents = round(sig.entry_price * 100)
        count = self.risk.position_size(sig.edge, price_cents, balance_usd)
        if count <= 0:
            log.info(f"Skipping {sig.kalshi_ticker} — position size is 0 (balance too low?)")
            return

        label = "[DRY RUN] " if self.dry_run else ""
        log.info(
            f"{label}Order: {sig.kalshi_ticker} "
            f"BUY {count}x {sig.side.upper()} @ {price_cents}¢ | {sig.description}"
        )

        if self.dry_run:
            return

        try:
            result = self.kalshi.place_order(
                ticker=sig.kalshi_ticker,
                side=sig.side,
                action="buy",
                count=count,
                limit_price=price_cents,
            )
            order_id = result.get("order", {}).get("order_id", "?")
            log.info(f"Order placed: {order_id}")
            self.risk.record_fill(sig.kalshi_ticker, sig.side, count, price_cents, "buy")
        except Exception as e:
            log.error(f"Order failed for {sig.kalshi_ticker}: {e}")
