"""
Kalshi World Cup Daily Strategy Dashboard
Run: streamlit run dashboard.py
"""
import sys
import time
import streamlit as st

sys.path.insert(0, ".")
from src.strategy import Signal
from src.price_model import trade_scenarios

st.set_page_config(
    page_title="Kalshi WC Daily Strategy",
    page_icon="⚽",
    layout="wide",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .card {
    background: #1a1f2e !important;
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 18px;
    border: 1px solid #2a3147;
  }
  .card-header {
    display: flex; justify-content: space-between; align-items: flex-start;
    flex-wrap: wrap; gap: 8px; margin-bottom: 6px;
  }
  .game-title { font-size: 18px; font-weight: 700; color: #ffffff !important; }
  .game-date  { font-size: 12px; color: #7a88a8 !important; margin-top: 2px; }
  .badge-yes { background: #0d6e2b; color: #6dffa0 !important; padding: 4px 12px;
               border-radius: 20px; font-size: 12px; font-weight: 700; white-space: nowrap; }
  .badge-no  { background: #6e1f0d; color: #ffcc99 !important; padding: 4px 12px;
               border-radius: 20px; font-size: 12px; font-weight: 700; white-space: nowrap; }

  /* Opportunity headline */
  .opp-headline {
    font-size: 20px; font-weight: 800; color: #ffffff !important;
    margin: 14px 0 6px 0; line-height: 1.25;
  }
  .opp-why {
    font-size: 14px; color: #c0cce0 !important; line-height: 1.6;
    margin-bottom: 16px;
  }
  .opp-why b { color: #ffffff !important; }
  .opp-why .hi { color: #5defa0 !important; font-weight: 700; }
  .opp-why .lo { color: #ff9966 !important; font-weight: 700; }

  /* Play steps */
  .play-block { display: flex; flex-direction: column; gap: 10px; margin-bottom: 6px; }
  .play-row {
    display: flex; align-items: flex-start; gap: 10px; flex-wrap: wrap;
    background: #111825; border-radius: 10px; padding: 12px 14px;
  }
  .play-icon {
    font-size: 18px; flex-shrink: 0; margin-top: 1px; width: 26px; text-align: center;
  }
  .play-content { flex: 1; min-width: 0; }
  .play-label {
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.07em; color: #7a88a8 !important; margin-bottom: 3px;
  }
  .play-text {
    font-size: 14px; color: #dce6f5 !important; line-height: 1.5;
  }
  .play-text b  { color: #ffffff !important; }
  .play-text .g { color: #5defa0 !important; font-weight: 700; }
  .play-text .r { color: #ff7070 !important; font-weight: 700; }
  .play-text .m { color: #a8b4cc !important; }
  .play-text .y { color: #ffd966 !important; font-weight: 700; }

  .divider { border-top: 1px solid #2a3147; margin: 14px 0; }
  .ticker-line { font-size: 11px; color: #4a5570 !important; margin-top: 12px; }
  .green { color: #5defa0 !important; font-weight: 700; }
  .gray  { color: #7a88a8 !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## ⚽ Kalshi World Cup — Daily Strategy")
st.markdown("*Opportunities where Kalshi pricing diverges from major sportsbook consensus*")
st.divider()

# ── Controls ──────────────────────────────────────────────────────────────────
col_stake, col_threshold, col_refresh = st.columns([1, 1, 1])
with col_stake:
    stake = st.number_input("Stake per trade ($)", min_value=1, max_value=500, value=10, step=5)
with col_threshold:
    threshold_pct = st.slider("Min edge threshold (%)", min_value=1, max_value=10, value=2, step=1)
    threshold = threshold_pct / 100
with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    refresh = st.button("🔄 Refresh scan", use_container_width=True)

st.divider()

# ── Scanner ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)   # cache 15 minutes
def run_scan(edge_threshold: float) -> list[Signal]:
    import os
    os.environ["EDGE_THRESHOLD"] = str(edge_threshold)
    import importlib, src.config as cfg
    importlib.reload(cfg)
    import src.strategy as strat
    importlib.reload(strat)
    from src.strategy import Strategy as S
    return S().scan()

if refresh:
    st.cache_data.clear()

with st.spinner("Scanning Kalshi + odds API..."):
    try:
        signals = run_scan(threshold)
    except Exception as e:
        st.error(f"Scan error: {e}")
        st.stop()

if not signals:
    st.info("No opportunities found above the edge threshold. Try lowering it or check back later.")
    st.stop()

st.success(f"Found **{len(signals)} opportunities** across {len(set(s.game_date for s in signals))} game days")

# ── Group by date ─────────────────────────────────────────────────────────────
from collections import defaultdict
from datetime import datetime

def _date_sort_key(date_str: str) -> tuple:
    """Sort 'Jun 22', 'Jun 23' etc chronologically."""
    try:
        return datetime.strptime(f"{date_str} 2026", "%b %d %Y").timetuple()[:3]
    except Exception:
        return (9999,)

by_date: dict[str, list] = defaultdict(list)
for s in signals:
    by_date[s.game_date or "Unknown"].append(s)

sorted_dates = sorted(by_date.keys(), key=_date_sort_key)

# ── Render cards ──────────────────────────────────────────────────────────────
def render_card(sig: Signal, stake_usd: float):
    sc = trade_scenarios(
        outcome=sig.outcome,
        side=sig.side,
        entry_price=sig.entry_price,
        p_a=sig.p_team_a,
        p_b=sig.p_team_b,
        p_t=sig.p_tie,
        team_a_name=sig.team_a,
        team_b_name=sig.team_b,
        stake_usd=stake_usd,
    )

    badge = (
        '<span class="badge-yes">BUY YES</span>' if sig.side == "yes"
        else '<span class="badge-no">BUY NO (short)</span>'
    )

    # Which team's goal helps vs hurts us?
    if sig.side == "yes":
        if sig.outcome.lower() in (sig.team_a.lower(), sig.team_a.lower().split()[0]):
            good_scorer, bad_scorer = "A", "B"
        elif sig.outcome.lower() in (sig.team_b.lower(), sig.team_b.lower().split()[0]):
            good_scorer, bad_scorer = "B", "A"
        else:
            good_scorer, bad_scorer = None, None
    else:
        if sig.outcome.lower() in (sig.team_a.lower(), sig.team_a.lower().split()[0]):
            good_scorer, bad_scorer = "B", "A"
        elif sig.outcome.lower() in (sig.team_b.lower(), sig.team_b.lower().split()[0]):
            good_scorer, bad_scorer = "A", "B"
        else:
            good_scorer, bad_scorer = None, None

    sc_a = sc["if_A_scores_first"]
    sc_b = sc["if_B_scores_first"]
    cost_usd = sc["cost_usd"]
    contracts = sc["contracts"]
    entry_c  = round(sig.entry_price * 100)
    fair_c   = round(sig.fair_prob * 100)

    if good_scorer == "A":
        good_sc, good_team = sc_a, sig.team_a
        bad_sc,  bad_team  = sc_b, sig.team_b
        good_p = sc["p_A_scores_first"]
        bad_p  = sc["p_B_scores_first"]
    elif good_scorer == "B":
        good_sc, good_team = sc_b, sig.team_b
        bad_sc,  bad_team  = sc_a, sig.team_a
        good_p = sc["p_B_scores_first"]
        bad_p  = sc["p_A_scores_first"]
    else:
        good_sc = bad_sc = good_team = bad_team = None
        good_p  = bad_p = 0.5

    # ── Narrative: headline + why ─────────────────────────────────────────────
    if sig.side == "yes":
        headline = f"{sig.outcome} looks undervalued — Kalshi hasn't caught up to the books yet"
        why_html = (
            f"Major sportsbooks across 10+ platforms give <b>{sig.outcome}</b> a "
            f"<span class='hi'>{fair_c}%</span> chance to win. "
            f"Kalshi is still pricing them at <span class='lo'>{entry_c}¢</span> — "
            f"a <b>{sig.edge:.0%} gap</b> in your favor. "
            f"That gap is your edge: buy now before the market corrects."
        )
    else:
        kalshi_yes_c = round((1 - sig.entry_price) * 100)
        other_team = sig.team_b if sig.outcome.lower() in sig.team_a.lower() else sig.team_a
        headline = f"{sig.outcome} is overpriced on Kalshi — the crowd is too confident"
        why_html = (
            f"Kalshi bettors are pricing <b>{sig.outcome}</b> at "
            f"<span class='lo'>{kalshi_yes_c}¢</span> to win, but major sportsbooks "
            f"only give them <span class='hi'>{fair_c}%</span>. "
            f"Buying NO means you're betting against the hype — "
            f"you win if <b>{other_team}</b> wins or the match draws."
        )

    # ── Steps ────────────────────────────────────────────────────────────────
    buy_text = (
        f"Buy <b>{contracts} contracts</b> at <b>{entry_c}¢ each</b> = "
        f"<b>${cost_usd:.2f} total</b>. "
        f"<span class='m'>Your 2× exit price is {entry_c * 2}¢ per contract (${cost_usd * 2:.2f} back).</span>"
    )

    if good_sc:
        good_roi    = good_sc["roi"]
        good_exit_c = round(good_sc["exit_price"] * 100)
        good_payout = good_sc["payout_usd"]
        bad_roi     = bad_sc["roi"]
        bad_exit_c  = round(bad_sc["exit_price"] * 100)
        bad_payout  = bad_sc["payout_usd"]
        multiplier  = round(1 + good_roi, 1)
        hits_2x     = good_roi >= 0.90

        if hits_2x:
            sell_result = f"<span class='g'>${good_payout:.2f} back — that's {multiplier:.1f}× your money ✓</span>"
        else:
            sell_result = f"<span class='y'>${good_payout:.2f} back (+{good_roi:.0%}) — not quite 2× but solid</span>"

        # Sell: target is when team LEADS, not just scores
        sell_text = (
            f"Your best exit is when <b>{good_team} takes the lead</b> — "
            f"that's when the contract peaks, not just when they score. "
            f"If they score to go ahead (1-0, 2-1, etc.), price jumps to ~<b>{good_exit_c}¢</b> → {sell_result}. "
            f"<span class='m'>Pro tip: if they equalize first (e.g., 1-1), consider selling half your position "
            f"to lock in recovery, and ride the rest for the lead.</span>"
        )

        # Wrong: time-aware, patient advice
        wrong_text = (
            f"If <b>{bad_team}</b> scores first — <b>don't panic sell</b>. Timing in soccer is everything:<br>"
            f"<span class='m'>• <b>Before min 45:</b> Hold comfortably. A goal this early means little — "
            f"{good_team} has a full half to respond. Price will recover if they equalize.</span><br>"
            f"<span class='m'>• <b>Min 45–65:</b> Stay patient. Watch the momentum. "
            f"If {good_team} is pressing and creating chances, hold. If they look flat, consider a partial exit.</span><br>"
            f"<span class='m'>• <b>Min 65–75:</b> If still down, start watching to exit. "
            f"When {good_team} equalizes — that's your sell signal, don't wait for the lead.</span><br>"
            f"<span class='m'>• <b>After min 75:</b> Window is closing. If still trailing, "
            f"cut your loss now rather than risk full collapse.</span><br>"
            f"<b>The real rule:</b> sell when {good_team} ties or leads, not when the other team scores."
        )

        # Side play — before game AND in-game Tie spike
        if sig.side == "yes" and sig.p_tie >= 0.20:
            side_play = (
                f"<b>Before the game:</b> consider $2–3 on Tie — "
                f"books give this match a <b>{sig.p_tie:.0%} draw chance</b>, which is meaningful. "
                f"<b>During the game:</b> if the score reaches 1-1 after minute 55, "
                f"quickly buy a small Tie position — draw contracts spike when it's even late, "
                f"and you can flip it for a fast gain whether your main bet holds or not. "
                f"This is exactly how you can make money even when the game goes sideways."
            )
        elif sig.side == "no":
            other = sig.team_b if sig.outcome.lower() in sig.team_a.lower() else sig.team_a
            side_play = (
                f"Pair with a small <b>YES on {other}</b>. "
                f"Both positions profit if {sig.outcome} underperforms — "
                f"you're covered whether {other} wins or the game draws."
            )
        else:
            side_play = None
    else:
        # Tie contract
        sell_text = (
            f"Hold through the first half. If the game is still 0-0 past <b>minute 65</b>, "
            f"Tie contracts will climb fast as the draw becomes more likely. "
            f"Sell when you're up <b>80–100%</b> — don't wait for full time, "
            f"because one late goal collapses the price instantly."
        )
        wrong_text = (
            f"If either team scores in the <b>first 60 minutes</b>, hold briefly — "
            f"late equalizers happen often in soccer and would spike your Tie value. "
            f"But if a goal comes <b>after minute 70</b> with the game still 1-0, "
            f"<span class='r'>exit quickly</span> — the window for a draw is closing fast."
        )
        side_play = None

    side_play_row = ""
    if side_play:
        side_play_row = f"""
        <div class="play-row">
          <div class="play-icon">💡</div>
          <div class="play-content">
            <div class="play-label">Side play</div>
            <div class="play-text">{side_play}</div>
          </div>
        </div>"""

    with st.container():
        st.markdown(f"""
        <div class="card">
          <div class="card-header">
            <div>
              <div class="game-title">{sig.game_title}</div>
              <div class="game-date">{sig.game_date}</div>
            </div>
            <div>{badge}</div>
          </div>

          <div class="opp-headline">{headline}</div>
          <div class="opp-why">{why_html}</div>

          <div class="play-block">
            <div class="play-row">
              <div class="play-icon">①</div>
              <div class="play-content">
                <div class="play-label">Buy now</div>
                <div class="play-text">{buy_text}</div>
              </div>
            </div>
            <div class="play-row">
              <div class="play-icon">🎯</div>
              <div class="play-content">
                <div class="play-label">When to sell</div>
                <div class="play-text">{sell_text}</div>
              </div>
            </div>
            {side_play_row}
            <div class="play-row">
              <div class="play-icon">⚠️</div>
              <div class="play-content">
                <div class="play-label">If it goes wrong</div>
                <div class="play-text">{wrong_text}</div>
              </div>
            </div>
          </div>

          <div class="ticker-line">
            Edge vs books: +{sig.edge:.1%} &nbsp;·&nbsp;
            Fair value: {fair_c}¢ &nbsp;·&nbsp;
            Kalshi entry: {entry_c}¢ &nbsp;·&nbsp;
            EV: ${sc["expected_value_usd"]:.2f} &nbsp;·&nbsp;
            Ticker: {sig.kalshi_ticker}
          </div>
        </div>
        """, unsafe_allow_html=True)


for date in sorted_dates:
    day_sigs = by_date[date]
    yes_sigs = sorted([s for s in day_sigs if s.side == "yes"], key=lambda x: -x.roi_target)
    no_sigs  = sorted([s for s in day_sigs if s.side == "no"],  key=lambda x: -x.roi_target)

    # Today or tomorrow get expanded by default
    is_soon = sorted_dates.index(date) < 2
    label = f"📅 **{date}** — {len(day_sigs)} signal{'s' if len(day_sigs) != 1 else ''}"
    if yes_sigs:
        label += f"  🟢 {len(yes_sigs)} BUY YES"
    if no_sigs:
        label += f"  🟠 {len(no_sigs)} BUY NO"

    with st.expander(label, expanded=is_soon):
        if yes_sigs:
            st.markdown("#### 🟢 Buy YES — Kalshi underpricing")
            for sig in yes_sigs:
                render_card(sig, stake)

        if no_sigs:
            st.markdown("#### 🟠 Buy NO — Short overpriced favorites")
            st.caption("Kalshi prices these favorites higher than sharp books. Buy NO = bet the favorite DOESN'T win.")
            for sig in no_sigs:
                render_card(sig, stake)

st.divider()
st.markdown(
    "<div style='color:#5a6580; font-size:12px;'>"
    "Prices from Kalshi API + The Odds API (10+ bookmakers). "
    "First-goal cash-out estimates use a historical first-goal win-rate model (~73% for scoring team). "
    "Not financial advice. "
    f"Last refreshed: {time.strftime('%H:%M:%S')}"
    "</div>",
    unsafe_allow_html=True
)
