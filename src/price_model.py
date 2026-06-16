"""
First-goal price impact model for soccer.

After team A scores the first goal:
  - Historical data: the scoring team wins ~73% of matches overall
  - We adjust upward for strong favorites, downward for underdogs
  - We then re-normalize across all three outcomes (home win / draw / away win)

Returns estimated Kalshi YES prices (in dollars) post-goal.
"""


def _clamp(x: float, lo=0.01, hi=0.99) -> float:
    return max(lo, min(hi, x))


def post_goal_probs(
    p_a: float,  # pre-game P(team A wins)
    p_b: float,  # pre-game P(team B wins)
    p_t: float,  # pre-game P(tie)
    scoring_team: str,  # "A" or "B"
) -> tuple[float, float, float]:
    """
    Returns (P_a_wins, P_b_wins, P_tie) after the first goal.

    Model:
      - Base: scoring team wins ~73% after scoring first
      - Adjusted ±10% based on pre-game strength
      - Draw becomes much less likely (~1/3 of original)
      - Other team picks up the remainder
    """
    # Base win rate for the team that scores first, adjusted for quality
    BASE_WIN_AFTER_GOAL = 0.73

    if scoring_team == "A":
        strength_adj = 0.10 * (p_a - 0.40)
        p_a_new = _clamp(BASE_WIN_AFTER_GOAL + strength_adj)
        p_t_new = _clamp(p_t * 0.30)
        p_b_new = _clamp(1 - p_a_new - p_t_new)
    else:
        strength_adj = 0.10 * (p_b - 0.40)
        p_b_new = _clamp(BASE_WIN_AFTER_GOAL + strength_adj)
        p_t_new = _clamp(p_t * 0.30)
        p_a_new = _clamp(1 - p_b_new - p_t_new)

    # Normalize
    total = p_a_new + p_b_new + p_t_new
    return p_a_new / total, p_b_new / total, p_t_new / total


def trade_scenarios(
    outcome: str,       # "Team A name" / "Team B name" / "Tie"
    side: str,          # "yes" or "no"
    entry_price: float, # what we pay per contract
    p_a: float,
    p_b: float,
    p_t: float,
    team_a_name: str,
    team_b_name: str,
    stake_usd: float = 5.0,
) -> dict:
    """
    Returns a scenario dict for a given trade:
      - contracts purchased
      - value after team A scores first
      - value after team B scores first
      - probability of each scenario
      - expected value
    """
    contracts = int(stake_usd / entry_price)
    cost = contracts * entry_price

    # Which outcome does our contract track?
    if outcome.lower() in ("tie", "draw", "tbd"):
        outcome_key = "tie"
    elif outcome.lower() in (team_a_name.lower(), team_a_name.lower().split()[0]):
        outcome_key = "A"
    else:
        outcome_key = "B"

    results = {}
    for scorer in ("A", "B"):
        pa, pb, pt = post_goal_probs(p_a, p_b, p_t, scorer)

        if outcome_key == "A":
            post_prob = pa
        elif outcome_key == "B":
            post_prob = pb
        else:
            post_prob = pt

        if side == "yes":
            exit_price = post_prob
        else:
            exit_price = 1 - post_prob

        payout = contracts * exit_price
        roi = (payout - cost) / cost if cost > 0 else 0
        results[scorer] = {
            "exit_price": round(exit_price, 3),
            "payout_usd": round(payout, 2),
            "roi": round(roi, 3),
        }

    # Probability that team A scores first vs team B scores first
    # Simple approximation: proportional to attack strength ≈ pre-game win probability
    p_a_scores_first = p_a / (p_a + p_b) if (p_a + p_b) > 0 else 0.5
    p_b_scores_first = 1 - p_a_scores_first

    ev = (
        p_a_scores_first * results["A"]["payout_usd"]
        + p_b_scores_first * results["B"]["payout_usd"]
    )

    return {
        "contracts": contracts,
        "cost_usd": round(cost, 2),
        "if_A_scores_first": results["A"],
        "if_B_scores_first": results["B"],
        "p_A_scores_first": round(p_a_scores_first, 3),
        "p_B_scores_first": round(p_b_scores_first, 3),
        "expected_value_usd": round(ev, 2),
        "team_a_name": team_a_name,
        "team_b_name": team_b_name,
    }
