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
  .game-title { font-size: 20px; font-weight: 700; color: #ffffff !important; }
  .game-date  { font-size: 14px; color: #7a88a8 !important; margin-top: 3px; }
  .badge-yes { background: #0d6e2b; color: #6dffa0 !important; padding: 5px 14px;
               border-radius: 20px; font-size: 13px; font-weight: 700; white-space: nowrap; }
  .badge-no  { background: #6e1f0d; color: #ffcc99 !important; padding: 5px 14px;
               border-radius: 20px; font-size: 13px; font-weight: 700; white-space: nowrap; }

  /* Opportunity headline */
  .opp-headline {
    font-size: 22px; font-weight: 800; color: #ffffff !important;
    margin: 16px 0 8px 0; line-height: 1.3;
  }
  .opp-why {
    font-size: 16px; color: #c0cce0 !important; line-height: 1.7;
    margin-bottom: 18px;
  }
  .opp-why b { color: #ffffff !important; }
  .opp-why .hi { color: #5defa0 !important; font-weight: 700; }
  .opp-why .lo { color: #ff9966 !important; font-weight: 700; }

  /* Play steps */
  .play-block { display: flex; flex-direction: column; gap: 12px; margin-bottom: 6px; }
  .play-row {
    display: flex; align-items: flex-start; gap: 12px; flex-wrap: wrap;
    background: #111825; border-radius: 10px; padding: 14px 16px;
  }
  .play-icon {
    font-size: 20px; flex-shrink: 0; margin-top: 2px; width: 28px; text-align: center;
  }
  .play-content { flex: 1; min-width: 0; }
  .play-label {
    font-size: 12px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.07em; color: #7a88a8 !important; margin-bottom: 5px;
  }
  .play-text {
    font-size: 16px; color: #dce6f5 !important; line-height: 1.6;
  }
  .play-text b  { color: #ffffff !important; }
  .play-text .g { color: #5defa0 !important; font-weight: 700; }
  .play-text .r { color: #ff7070 !important; font-weight: 700; }
  .play-text .m { color: #b0bcd0 !important; }
  .play-text .y { color: #ffd966 !important; font-weight: 700; }

  .divider { border-top: 1px solid #2a3147; margin: 14px 0; }
  .ticker-line { font-size: 13px; color: #4a5570 !important; margin-top: 12px; }
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
WATCH_THRESHOLD = 0.01   # always scan at ≥1% to show same-day games

@st.cache_data(ttl=900, show_spinner=False)
def run_scan(_cache_key: float) -> list[Signal]:
    import os
    # Scan wide — always pull everything ≥1% so same-day games appear
    os.environ["EDGE_THRESHOLD"] = str(WATCH_THRESHOLD)
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
        all_signals = run_scan(threshold)
    except Exception as e:
        st.error(f"Scan error: {e}")
        st.stop()

# Split: actionable (above user slider) vs watching (1%–slider)
signals      = [s for s in all_signals if s.edge >= threshold]
watch_signals = [s for s in all_signals if s.edge < threshold]

if not all_signals:
    st.info("No opportunities found. Try refreshing or check back later.")
    st.stop()

hot_count   = len(signals)
watch_count = len(watch_signals)
total_days  = len(set(s.game_date for s in all_signals))
st.success(
    f"Found **{hot_count} actionable** {'opportunity' if hot_count == 1 else 'opportunities'} "
    f"+ **{watch_count} watching** across {total_days} game days"
)

# ── Shared helpers ────────────────────────────────────────────────────────────
from collections import defaultdict
from datetime import datetime

def _date_sort_key(date_str: str) -> tuple:
    try:
        return datetime.strptime(f"{date_str} 2026", "%b %d %Y").timetuple()[:3]
    except Exception:
        return (9999,)

def _edge_emoji(edge: float) -> str:
    if edge >= 0.05: return "🟢"
    if edge >= 0.03: return "🟠"
    if edge >= 0.02: return "🟡"
    return "🔴"

# ── Portfolio Builder ──────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def fetch_balance() -> float:
    from src.kalshi_client import KalshiClient
    try:
        data = KalshiClient().get_balance()
        # balance is in cents
        return round(data.get("balance", 0) / 100, 2)
    except Exception:
        return 0.0

with st.expander("💼 Portfolio Builder — spread your budget across signals", expanded=False):
    if not signals:
        st.info("No actionable signals right now. Lower the edge threshold to see more options.")
    else:
        kalshi_balance = fetch_balance()

        bal_col, budget_col = st.columns([1, 2])
        with bal_col:
            if kalshi_balance > 0:
                st.metric("Your Kalshi balance", f"${kalshi_balance:.2f}")
            else:
                st.warning("⚠️ Could not fetch Kalshi balance — enter budget manually.")
        with budget_col:
            pb_budget = st.number_input(
                "Budget to deploy ($)",
                min_value=1.0,
                max_value=float(kalshi_balance) if kalshi_balance > 0 else 500.0,
                value=float(kalshi_balance) if kalshi_balance > 0 else 5.0,
                step=0.5,
                key="pb_budget",
                help="Defaults to your full Kalshi balance. Lower it to keep some cash in reserve."
            )

        st.caption("Pick the signals you want to play — we'll split your budget weighted by edge strength.")

        # Checkboxes grouped by date with edge color
        pb_by_date: dict[str, list] = defaultdict(list)
        for sig in signals:
            pb_by_date[sig.game_date or "Unknown"].append(sig)
        pb_sorted_dates = sorted(pb_by_date.keys(), key=_date_sort_key)

        selected_keys = []
        for pb_date in pb_sorted_dates:
            day_sigs = sorted(pb_by_date[pb_date], key=lambda x: -x.edge)
            st.markdown(f"**📅 {pb_date}**")
            for sig in day_sigs:
                side_label = "YES" if sig.side == "yes" else "NO"
                dot = _edge_emoji(sig.edge)
                label = (
                    f"{dot} **{sig.game_title}** — "
                    f"{sig.outcome} {side_label} · Edge **+{sig.edge:.1%}** · "
                    f"Kalshi: {round(sig.entry_price*100)}¢ · Books: {round(sig.fair_prob*100)}%"
                )
                if st.checkbox(label, key=f"pb_{sig.kalshi_ticker}"):
                    selected_keys.append(sig.kalshi_ticker)

        selected_sigs = [s for s in signals if s.kalshi_ticker in selected_keys]

        if selected_sigs:
            st.divider()
            st.markdown("#### 📊 Your allocation plan")

            # Edge-weighted allocation, minimum $1 per bet
            total_edge = sum(s.edge for s in selected_sigs)
            raw_allocs = {s.kalshi_ticker: (s.edge / total_edge) * pb_budget for s in selected_sigs}

            # Enforce $1 minimum — scale down others if needed
            min_alloc = 1.0
            allocs = {}
            for s in selected_sigs:
                allocs[s.kalshi_ticker] = max(min_alloc, round(raw_allocs[s.kalshi_ticker] * 2) / 2)

            # Trim total back to budget if rounding pushed it over
            total_alloc = sum(allocs.values())
            if total_alloc > pb_budget:
                largest = max(allocs, key=allocs.get)
                allocs[largest] -= (total_alloc - pb_budget)
                allocs[largest] = round(allocs[largest] * 2) / 2

            # Summary table
            total_cost = 0
            total_ev   = 0
            rows = []
            for sig in selected_sigs:
                alloc    = allocs[sig.kalshi_ticker]
                entry_c  = round(sig.entry_price * 100)
                n_contracts = int(alloc / sig.entry_price)
                cost     = round(n_contracts * sig.entry_price, 2)
                ev       = round(cost * (1 + sig.roi_target), 2)
                total_cost += cost
                total_ev   += ev
                rows.append({
                    "Game": sig.game_title,
                    "Date": sig.game_date,
                    "Bet": f"{sig.outcome} {'YES' if sig.side=='yes' else 'NO'}",
                    "Allocate": f"${alloc:.2f}",
                    "Contracts": n_contracts,
                    "Entry": f"{entry_c}¢",
                    "Edge": f"+{sig.edge:.1%}",
                    "If wins → est.": f"${ev:.2f}",
                })

            import pandas as pd
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            col1, col2, col3 = st.columns(3)
            col1.metric("Total deployed", f"${total_cost:.2f}", f"of ${pb_budget:.2f} budget")
            col2.metric("Expected return", f"${total_ev:.2f}", f"+{(total_ev/total_cost - 1):.0%} blended EV")
            col3.metric("Signals selected", len(selected_sigs))

            st.caption(
                "Allocation is weighted by edge — stronger mispricings get more of your budget. "
                "Minimum $1 per bet. 'If wins' assumes price reaches fair value (not full $1 payout)."
            )
        elif not selected_keys and signals:
            st.info("Check the signals above to see your portfolio plan.")

st.divider()

# ── Group by date ─────────────────────────────────────────────────────────────
by_date: dict[str, list] = defaultdict(list)
for s in all_signals:
    by_date[s.game_date or "Unknown"].append(s)

sorted_dates = sorted(by_date.keys(), key=_date_sort_key)

def _day_grade(sigs: list, user_threshold: float) -> tuple[str, str]:
    """Return (emoji, label) for the day based on best edge found."""
    actionable = [s for s in sigs if s.edge >= user_threshold]
    best = max((s.edge for s in sigs), default=0)
    if actionable and best >= 0.05:
        return "🟢", "STRONG"
    elif actionable and best >= 0.03:
        return "🟠", "GOOD"
    elif actionable:
        return "🟡", "MODERATE"
    else:
        return "🔴", "WATCHING"

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
    elif good_scorer == "B":
        good_sc, good_team = sc_b, sig.team_b
        bad_sc,  bad_team  = sc_a, sig.team_a
    else:
        good_sc = bad_sc = good_team = bad_team = None

    # ── Narrative: headline + action + why ───────────────────────────────────
    if sig.side == "yes":
        headline    = f"Buy {sig.outcome} to win — they're priced too cheap on Kalshi right now"
        kalshi_action = (
            f"On Kalshi: search <b>\"{sig.game_title}\"</b> → tap <b>{sig.outcome}</b> → tap <b>YES</b> → buy"
        )
        why_html = (
            f"Major sportsbooks across 10+ platforms give <b>{sig.outcome}</b> a "
            f"<span class='hi'>{fair_c}%</span> chance to win. "
            f"Kalshi is pricing them at only <span class='lo'>{entry_c}¢</span> — "
            f"<b>{sig.edge:.0%} below what they should be.</b> "
            f"That discount is your edge. Buy now before Kalshi catches up."
        )
    else:
        kalshi_yes_c = round((1 - sig.entry_price) * 100)
        other_team   = sig.team_b if sig.outcome.lower() in sig.team_a.lower() else sig.team_a
        headline     = f"Bet against {sig.outcome} — back {other_team} or a draw instead"
        kalshi_action = (
            f"On Kalshi: search <b>\"{sig.game_title}\"</b> → tap <b>{sig.outcome}</b> → tap <b>NO</b> → buy. "
            f"<span class='m'>(Buying NO on {sig.outcome} = you win if {other_team} wins OR the game draws.)</span>"
        )
        why_html = (
            f"Kalshi has <b>{sig.outcome}</b> at <span class='lo'>{kalshi_yes_c}¢</span> to win — "
            f"but real sportsbooks only price them at <span class='hi'>{fair_c}%</span>. "
            f"The Kalshi crowd is too bullish on {sig.outcome}. "
            f"Buying NO costs <b>{entry_c}¢</b> and pays $1 if {sig.outcome} fails to win — "
            f"either {other_team} wins or it ends in a draw."
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
            <div class="play-row" style="background:#0d1e36; border:1px solid #1e3a5f;">
              <div class="play-icon">📲</div>
              <div class="play-content">
                <div class="play-label">Kalshi action</div>
                <div class="play-text">{kalshi_action}</div>
              </div>
            </div>
            <div class="play-row">
              <div class="play-icon">①</div>
              <div class="play-content">
                <div class="play-label">How much</div>
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
    day_sigs   = by_date[date]
    grade_emoji, grade_label = _day_grade(day_sigs, threshold)

    # Actionable vs watching for this day
    act_sigs   = sorted([s for s in day_sigs if s.edge >= threshold], key=lambda x: -x.edge)
    watch_sigs = sorted([s for s in day_sigs if s.edge < threshold],  key=lambda x: -x.edge)

    yes_act  = [s for s in act_sigs  if s.side == "yes"]
    no_act   = [s for s in act_sigs  if s.side == "no"]

    # First 2 dates auto-expand; STRONG days always expand
    is_soon = sorted_dates.index(date) < 2 or grade_label == "STRONG"

    label = f"{grade_emoji} **{date}** — {grade_label}"
    if act_sigs:
        label += f"  ·  {len(act_sigs)} actionable"
    if watch_sigs:
        label += f"  ·  {len(watch_sigs)} watching"

    with st.expander(label, expanded=is_soon):

        if act_sigs:
            if yes_act:
                st.markdown("#### 🟢 Buy YES — underpriced on Kalshi")
                for sig in yes_act:
                    render_card(sig, stake)
            if no_act:
                st.markdown("#### 🟠 Bet against — overpriced favorites")
                for sig in no_act:
                    render_card(sig, stake)

        if watch_sigs:
            st.markdown("##### 👀 Watching — edge below your threshold")
            for sig in watch_sigs:
                edge_pct = f"+{sig.edge:.1%}"
                entry_c  = round(sig.entry_price * 100)
                fair_c   = round(sig.fair_prob * 100)
                action   = "BUY YES" if sig.side == "yes" else f"BUY NO (back {sig.team_b if sig.outcome.lower() in sig.team_a.lower() else sig.team_a})"
                st.markdown(
                    f"**{sig.game_title}** — {sig.outcome} · {action} · "
                    f"Kalshi: {entry_c}¢ · Books: {fair_c}% · Edge: **{edge_pct}** · "
                    f"_Lower threshold to see full plan_"
                )

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
