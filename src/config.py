import os
from dotenv import load_dotenv

load_dotenv()

KALSHI_ENV = os.getenv("KALSHI_ENV", "demo")

if KALSHI_ENV == "prod":
    KALSHI_HOST = "https://api.elections.kalshi.com"
else:
    KALSHI_HOST = "https://demo-api.kalshi.co"

KALSHI_BASE_URL = KALSHI_HOST + "/trade-api/v2"

KALSHI_API_KEY_ID = os.getenv("KALSHI_API_KEY_ID", "")
KALSHI_PRIVATE_KEY_PATH = os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi_private_key.pem")

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"

MAX_POSITION_USD = float(os.getenv("MAX_POSITION_USD", "50"))
MAX_DAILY_LOSS_USD = float(os.getenv("MAX_DAILY_LOSS_USD", "100"))
EDGE_THRESHOLD = float(os.getenv("EDGE_THRESHOLD", "0.04"))
