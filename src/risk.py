from src.config import MAX_POSITION_USD, MAX_DAILY_LOSS_USD
from src.logger import log


class RiskManager:
    def __init__(self):
        self.daily_pnl: float = 0.0         # realized P&L today in USD
        self.open_positions: dict = {}       # ticker -> {side, count, avg_price}
        self._killed = False

    def kill(self):
        self._killed = True
        log.critical("KILL SWITCH ACTIVATED — no new orders will be placed")

    @property
    def is_killed(self) -> bool:
        return self._killed

    def check_daily_loss(self) -> bool:
        if self.daily_pnl <= -MAX_DAILY_LOSS_USD:
            log.error(f"Daily loss limit hit (${self.daily_pnl:.2f}). Killing bot.")
            self.kill()
            return False
        return True

    def position_size(self, signal_edge: float, price_cents: int, balance_usd: float) -> int:
        """
        Kelly-inspired sizing capped at MAX_POSITION_USD.
        Returns number of contracts to buy (each contract pays $1 if correct).
        """
        if self._killed:
            return 0

        prob = price_cents / 100
        kelly_fraction = signal_edge / (1 - prob) if prob < 1 else 0
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # cap at quarter-Kelly

        dollar_risk = balance_usd * kelly_fraction
        dollar_risk = min(dollar_risk, MAX_POSITION_USD)

        cost_per_contract = price_cents / 100
        contracts = int(dollar_risk / cost_per_contract)
        return max(contracts, 0)

    def record_fill(self, ticker: str, side: str, count: int, price_cents: int, action: str):
        cost = count * price_cents / 100
        if action == "buy":
            self.daily_pnl -= cost
            pos = self.open_positions.get(ticker, {"side": side, "count": 0, "avg_price": 0})
            total = pos["count"] + count
            pos["avg_price"] = (pos["count"] * pos["avg_price"] + count * price_cents) / total
            pos["count"] = total
            self.open_positions[ticker] = pos
        elif action == "sell":
            self.daily_pnl += cost
            pos = self.open_positions.get(ticker)
            if pos:
                pos["count"] -= count
                if pos["count"] <= 0:
                    del self.open_positions[ticker]

        log.info(f"P&L today: ${self.daily_pnl:+.2f} | Open positions: {len(self.open_positions)}")
        self.check_daily_loss()
