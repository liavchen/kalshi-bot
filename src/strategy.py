"""
World Cup arbitrage strategy.

Logic:
  1. Fetch all open KXWCGAME events from Kalshi
  2. For each game outcome, compare Kalshi price to fair probability from The Odds API
  3. BUY YES when Kalshi ask < fair value (buying cheap)
  4. BUY NO  when Kalshi bid > fair value (shorting overpriced favorites)
  5. Exit when price moves to fair value → target ROI achieved
"""
from dataclasses import dataclass
from src.odds_client import OddsClient, decimal_to_prob
from src.kalshi_client import KalshiClient
from src.config import EDGE_THRESHOLD
from src.logger import log

# Teams whose names differ between Kalshi titles and The Odds API
TEAM_ALIASES: dict[str, list[str]] = {
    "ir iran":                    ["iran"],
    "korea republic":             ["south korea"],
    "congo dr":                   ["dr congo", "democratic republic of congo"],
    "usa":                        ["united states"],
    "ivory coast":                ["cote d'ivoire", "côte d'ivoire"],
    "czechia":                    ["czech republic"],
    "cape verde":                 ["cabo verde"],
    "turkiye":                    ["turkey"],
    "curacao":                    ["curaçao", "curacao"],
    "bosnia and herzegovina":     ["bosnia & herzegovina", "bosnia-herzegovina", "bosnia"],
    "north macedonia":            ["macedonia"],
    "new zealand":                ["new zealand (nz)"],
    "guinea":                     ["guinea-bissau", "equatorial guinea"],
}


@dataclass
class Signal:
    kalshi_ticker: str
    side: str           # "yes" = buy YES (underdog cheap) | "no" = buy NO (favorite overpriced)
    entry_price: float  # price we pay to enter (dollars)
    exit_price: float   # current bid on the other side (what we'd get if we flipped now)
    fair_prob: float    # vig-removed probability from odds API
    edge: float         # absolute edge in probability points
    roi_target: float   # ROI if price moves to fair value
    game_title: str
    outcome: str        # "Argentina" / "Jordan" / "Tie"
    team_a: str         # home team name
    team_b: str         # away team name
    p_team_a: float     # fair win probability for team A
    p_team_b: float     # fair win probability for team B
    p_tie: float        # fair draw probability
    game_date: str      # e.g. "Jun 27"
    description: str


def _resolve_name(name: str) -> list[str]:
    """Return all known aliases for a team name (including itself)."""
    low = name.lower()
    variants = {low}
    for canonical, aliases in TEAM_ALIASES.items():
        if low == canonical or low in aliases:
            variants.add(canonical)
            variants.update(aliases)
    return list(variants)


def _find_odds_game(games: list, team_a: str, team_b: str) -> dict | None:
    """Match Kalshi event teams to an odds API game using aliases + fuzzy matching."""
    variants_a = _resolve_name(team_a)
    variants_b = _resolve_name(team_b)

    for game in games:
        home = game["home_team"].lower()
        away = game["away_team"].lower()
        all_names = home + " " + away

        a_match = any(v in all_names for v in variants_a) or \
                  any(w in all_names for w in team_a.lower().split() if len(w) > 3)
        b_match = any(v in all_names for v in variants_b) or \
                  any(w in all_names for w in team_b.lower().split() if len(w) > 3)

        if a_match and b_match:
            return game
    return None


def _team_prob(game: dict, outcome: str) -> float | None:
    """Vig-removed implied probability for an outcome across all bookmakers."""
    raw_probs: dict[str, list[float]] = {}
    for bookie in game.get("bookmakers", []):
        for market in bookie.get("markets", []):
            if market["key"] != "h2h":
                continue
            for o in market["outcomes"]:
                name = o["name"].lower()
                raw_probs.setdefault(name, []).append(decimal_to_prob(o["price"]))

    if not raw_probs:
        return None

    avg = {k: sum(v) / len(v) for k, v in raw_probs.items()}
    total = sum(avg.values())
    fair = {k: v / total for k, v in avg.items()}

    target = outcome.lower()
    if target in ("tie", "draw", "tbd"):
        return fair.get("draw") or fair.get("tie")

    # Try all aliases then fuzzy word match
    for variant in _resolve_name(target):
        if variant in fair:
            return fair[variant]
    for k, v in fair.items():
        if target in k or k in target:
            return v
    return None


def _parse_outcome_from_ticker(ticker: str) -> str:
    return ticker.rsplit("-", 1)[-1]


class Strategy:
    def __init__(self):
        self.kalshi = KalshiClient()
        self.odds = OddsClient()
        self._odds_cache: list = []

    def _get_wc_odds(self) -> list:
        if not self._odds_cache:
            try:
                self._odds_cache = self.odds.get_odds("worldcup")
            except Exception as e:
                log.error(f"Odds API error: {e}")
        return self._odds_cache

    def scan(self) -> list[Signal]:
        signals: list[Signal] = []
        games = self._get_wc_odds()
        if not games:
            log.warning("No odds data — skipping scan")
            return signals

        log.info("Fetching open KXWCGAME events from Kalshi...")
        resp = self.kalshi._get('/events', {'series_ticker': 'KXWCGAME', 'status': 'open', 'limit': 50})
        events = resp.get('events', [])
        log.info(f"Found {len(events)} open WC game events")

        for event in events:
            event_ticker = event['event_ticker']
            game_title = event.get('title', event_ticker)
            sub_title  = event.get('sub_title', '')  # e.g. "JOR vs ARG (Jun 27)"

            # Parse date from subtitle like "JOR vs ARG (Jun 27)"
            game_date = ""
            if '(' in sub_title and ')' in sub_title:
                game_date = sub_title[sub_title.rfind('(') + 1 : sub_title.rfind(')')]

            title_parts = game_title.split(' vs ')
            if len(title_parts) != 2:
                continue
            team_a, team_b = title_parts[0].strip(), title_parts[1].strip()

            odds_game = _find_odds_game(games, team_a, team_b)
            if not odds_game:
                log.debug(f"No odds match: {game_title}")
                continue

            # Get per-game fair probabilities (for price model)
            p_team_a = _team_prob(odds_game, team_a) or 0.33
            p_team_b = _team_prob(odds_game, team_b) or 0.33
            p_tie    = _team_prob(odds_game, "tie")  or max(0.01, 1 - p_team_a - p_team_b)
            # Re-normalize
            total = p_team_a + p_team_b + p_tie
            p_team_a /= total
            p_team_b /= total
            p_tie    /= total

            try:
                ev_resp = self.kalshi._get(f'/events/{event_ticker}')
            except Exception as e:
                log.debug(f"Event fetch error {event_ticker}: {e}")
                continue

            for market in ev_resp.get('markets', []):
                ticker = market['ticker']
                outcome = (market.get('subtitle')
                           or market.get('yes_sub_title')
                           or _parse_outcome_from_ticker(ticker))
                yes_ask = float(market.get('yes_ask_dollars') or 0)
                yes_bid = float(market.get('yes_bid_dollars') or 0)
                no_ask  = round(1 - yes_bid, 4)
                no_bid  = round(1 - yes_ask, 4)

                if yes_ask <= 0 or yes_ask >= 1:
                    continue

                fair_prob = _team_prob(odds_game, outcome)
                if fair_prob is None:
                    log.debug(f"No fair prob for '{outcome}' in {game_title}")
                    continue

                common = dict(
                    game_title=game_title,
                    outcome=outcome,
                    team_a=team_a,
                    team_b=team_b,
                    p_team_a=round(p_team_a, 4),
                    p_team_b=round(p_team_b, 4),
                    p_tie=round(p_tie, 4),
                    game_date=game_date,
                )

                # --- BUY YES: Kalshi ask is below fair value ---
                yes_edge = fair_prob - yes_ask
                if yes_edge >= EDGE_THRESHOLD:
                    roi = yes_edge / yes_ask
                    sig = Signal(
                        kalshi_ticker=ticker,
                        side="yes",
                        entry_price=yes_ask,
                        exit_price=yes_bid,
                        fair_prob=fair_prob,
                        edge=yes_edge,
                        roi_target=roi,
                        description=(
                            f"BUY YES | {game_title} — {outcome} | "
                            f"fair={fair_prob:.1%} ask={yes_ask:.2f} "
                            f"edge={yes_edge:+.1%} ROI={roi:.0%}"
                        ),
                        **common,
                    )
                    signals.append(sig)
                    log.info(f"SIGNAL: {sig.description}")

                # --- BUY NO: Kalshi ask is above fair value (favorite overpriced) ---
                no_edge = (1 - fair_prob) - no_ask
                if no_edge >= EDGE_THRESHOLD:
                    roi = no_edge / no_ask
                    sig = Signal(
                        kalshi_ticker=ticker,
                        side="no",
                        entry_price=no_ask,
                        exit_price=no_bid,
                        fair_prob=fair_prob,
                        edge=no_edge,
                        roi_target=roi,
                        description=(
                            f"BUY NO  | {game_title} — {outcome} | "
                            f"fair={fair_prob:.1%} no_ask={no_ask:.2f} "
                            f"edge={no_edge:+.1%} ROI={roi:.0%}"
                        ),
                        **common,
                    )
                    signals.append(sig)
                    log.info(f"SIGNAL: {sig.description}")

        self._odds_cache = []
        log.info(f"Scan complete — {len(signals)} signals")
        return signals
