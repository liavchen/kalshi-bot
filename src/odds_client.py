import requests
from src.config import ODDS_API_KEY, ODDS_API_BASE_URL
from src.logger import log

SPORT_KEYS = {
    "nfl": "americanfootball_nfl",
    "nba": "basketball_nba",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "worldcup": "soccer_fifa_world_cup",
    "world_cup": "soccer_fifa_world_cup",
    "soccer": "soccer_fifa_world_cup",
    "epl": "soccer_epl",
    "champions_league": "soccer_uefa_champs_league",
}


class OddsClient:
    def __init__(self):
        self.session = requests.Session()

    def _get(self, path: str, params: dict = None) -> dict | list:
        params = params or {}
        params["apiKey"] = ODDS_API_KEY
        resp = self.session.get(ODDS_API_BASE_URL + path, params=params, timeout=10)
        resp.raise_for_status()
        log.debug(f"Odds API quota remaining: {resp.headers.get('x-requests-remaining', '?')}")
        return resp.json()

    def get_sports(self) -> list:
        return self._get("/sports")

    def get_odds(self, sport: str, markets: str = "h2h", regions: str = "us") -> list:
        sport_key = SPORT_KEYS.get(sport.lower(), sport)
        games = self._get(f"/sports/{sport_key}/odds", {
            "markets": markets,
            "regions": regions,
            "oddsFormat": "decimal",
        })
        log.info(f"Fetched odds for {len(games)} {sport.upper()} games")
        return games

    def get_scores(self, sport: str, days_from: int = 1) -> list:
        sport_key = SPORT_KEYS.get(sport.lower(), sport)
        return self._get(f"/sports/{sport_key}/scores", {"daysFrom": days_from})


def american_to_prob(american: int) -> float:
    """Convert American odds to implied probability."""
    if american > 0:
        return 100 / (american + 100)
    return abs(american) / (abs(american) + 100)


def decimal_to_prob(decimal: float) -> float:
    """Convert decimal odds to implied probability (no vig removal)."""
    return 1 / decimal


def remove_vig(probs: list[float]) -> list[float]:
    """Normalize probabilities to remove bookmaker vig."""
    total = sum(probs)
    return [p / total for p in probs]
