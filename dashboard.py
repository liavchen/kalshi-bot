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
  /* Force dark background on all custom cards */
  .card {
    background: #1a1f2e !important;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    border: 1px solid #2a3147;
  }
  .game-title { font-size: 20px; font-weight: 700; color: #ffffff !important; margin-bottom: 2px; }
  .game-date  { font-size: 13px; color: #a8b4cc !important; margin-bottom: 14px; }
  .badge-yes  { background: #0d6e2b; color: #6dffa0 !important; padding: 4px 12px;
                border-radius: 20px; font-size: 12px; font-weight: 700; white-space: nowrap; }
  .badge-no   { background: #6e1f0d; color: #ffcc99 !important; padding: 4px 12px;
                border-radius: 20px; font-size: 12px; font-weight: 700; white-space: nowrap; }
  .metric-label { font-size: 11px; color: #a8b4cc !important; margin-bottom: 4px;
                  text-transform: uppercase; letter-spacing: 0.06em; }
  .metric-big   { font-size: 24px; font-weight: 700; color: #ffffff !important; line-height: 1.1; }
  .metric-sub   { font-size: 12px; color: #c8d0e0 !important; margin-top: 2px; }
  .scenario-block {
    background: #0d1117 !important;
    border: 1px solid #2a3147;
    border-radius: 8px;
    padding: 12px 16px;
    color: #e0e6f0 !important;
    font-size: 13px;
  }
  .scenario-block b { color: #ffffff !important; }
  .green { color: #5defa0 !important; font-weight: 700; }
  .red   { color: #ff7070 !important; font-weight: 700; }
  .gray  { color: #a8b4cc !important; }
  .divider { border-top: 1px solid #2a3147; margin: 14px 0; }
  .ticker-line { font-size: 11px; color: #6a7590 !important; margin-top: 10px; }

  /* Metrics row — wraps on mobile */
  .metrics-row {
    display: flex;
    flex-wrap: wrap;
    gap: 20px 32px;
    margin-bottom: 16px;
  }
  .metric-cell { min-width: 90px; }

  /* Scenarios row — stacks on mobile */
  .scenarios-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  .scenarios-row .scenario-block { flex: 1 1 240px; }

  /* Card header — badge wraps below on very small screens */
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 14px;
  }

  /* Game plan block */
  .game-plan {
    background: #0a0f1a;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 4px;
  }
  .gp-title {
    font-size: 12px;
    font-weight: 700;
    color: #7ab3e0 !important;
    letter-spacing: 0.08em;
    margin-bottom: 12px;
  }
  .gp-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }
  .gp-step {
    font-size: 11px;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 12px;
    white-space: nowrap;
    flex-shrink: 0;
    margin-top: 1px;
  }
  .buy-step  { background: #0d3d6e; color: #7ab3e0 !important; }
  .sell-step { background: #0d4a1f; color: #5defa0 !important; }
  .cut-step  { background: #4a1f0d; color: #ffaa70 !important; }
  .edge-step { background: #2a2f42; color: #a8b4cc !important; }
  .gp-body {
    font-size: 13px;
    color: #d0dae8 !important;
    line-height: 1.5;
  }
  .gp-body b { color: #ffffff !important; }
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
        else:  # Tie — neither team scoring helps us
            good_scorer, bad_scorer = None, None
    else:
        # Buying NO on team X — we want the OTHER team to score
        if sig.outcome.lower() in (sig.team_a.lower(), sig.team_a.lower().split()[0]):
            good_scorer, bad_scorer = "B", "A"   # we short team A → want B to score
        elif sig.outcome.lower() in (sig.team_b.lower(), sig.team_b.lower().split()[0]):
            good_scorer, bad_scorer = "A", "B"
        else:
            good_scorer, bad_scorer = None, None

    sc_a = sc["if_A_scores_first"]
    sc_b = sc["if_B_scores_first"]

    # ── Game plan calculations ────────────────────────────────────────────────
    cost_usd   = sc["cost_usd"]
    target_2x  = round(cost_usd * 2, 2)
    entry_c    = round(sig.entry_price * 100, 1)   # entry in cents
    target_c   = round(sig.entry_price * 2 * 100, 1)  # 2x in cents

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
        good_sc = bad_sc = None

    if good_sc:
        good_exit_c  = round(good_sc["exit_price"] * 100, 1)
        good_payout  = good_sc["payout_usd"]
        good_roi     = good_sc["roi"]
        bad_exit_c   = round(bad_sc["exit_price"] * 100, 1)
        bad_payout   = bad_sc["payout_usd"]
        bad_roi      = bad_sc["roi"]

        hits_2x = good_roi >= 0.95   # ≥95% ROI ≈ 2x
        sell_icon   = "🟢" if hits_2x else "🟡"
        sell_label  = "SELL — 2x reached ✓" if hits_2x else f"SELL — est. {good_roi:.0%} gain (below 2x)"
        sell_detail = f"sell all {sc['contracts']} contracts @ ~{good_exit_c:.0f}¢ → ${good_payout:.2f}"

        cut_roi_str = f"{bad_roi:.0%}" if bad_roi < 0 else f"+{bad_roi:.0%}"
        cut_color   = "red" if bad_roi < -0.20 else "gray"
        cut_label   = "CUT LOSS — price will drop" if bad_roi < -0.20 else "HOLD — small impact"
        cut_detail  = f"est. {bad_exit_c:.0f}¢ → ${bad_payout:.2f} ({cut_roi_str})"

        game_plan_html = f"""
        <div class="game-plan">
          <div class="gp-title">📋 GAME PLAN</div>
          <div class="gp-row">
            <span class="gp-step buy-step">① BUY NOW</span>
            <span class="gp-body">
              <b>{sc['contracts']} contracts</b> × {entry_c:.0f}¢ = <b>${cost_usd:.2f} total cost</b>
              &nbsp;·&nbsp; <span class="gray">2× target: {target_c:.0f}¢ per contract (${target_2x:.2f})</span>
            </span>
          </div>
          <div class="gp-row">
            <span class="gp-step sell-step">{sell_icon} SELL TRIGGER</span>
            <span class="gp-body">
              <b>{good_team}</b> scores first ({good_p:.0%} chance) → <span class="green">{sell_label}</span><br>
              <span class="gray">{sell_detail}</span>
            </span>
          </div>
          <div class="gp-row">
            <span class="gp-step cut-step">⚠ IF WRONG</span>
            <span class="gp-body">
              <b>{bad_team}</b> scores first ({bad_p:.0%} chance) → <span class="{cut_color}">{cut_label}</span><br>
              <span class="gray">{cut_detail} — your call to hold or exit</span>
            </span>
          </div>
          <div class="gp-row" style="margin-top:6px;">
            <span class="gp-step edge-step">💡 EDGE</span>
            <span class="gp-body gray">
              Books price this at {sig.fair_prob:.1%} · Kalshi sells it at {entry_c:.0f}¢ · you're buying {sig.edge:.1%} below fair value
            </span>
          </div>
        </div>"""
    else:
        # Tie contract — no single goal is the trigger
        game_plan_html = f"""
        <div class="game-plan">
          <div class="gp-title">📋 GAME PLAN</div>
          <div class="gp-row">
            <span class="gp-step buy-step">① BUY NOW</span>
            <span class="gp-body">
              <b>{sc['contracts']} contracts</b> × {entry_c:.0f}¢ = <b>${cost_usd:.2f}</b>
              &nbsp;·&nbsp; <span class="gray">2× target: {target_c:.0f}¢ (${target_2x:.2f})</span>
            </span>
          </div>
          <div class="gp-row">
            <span class="gp-step sell-step">🎯 SELL TRIGGER</span>
            <span class="gp-body">
              Sell if price rises toward <b>{target_c:.0f}¢</b> as the match approaches.<br>
              <span class="gray">TIE contracts gain value when the match stays level late. Watch at 60–75 min.</span>
            </span>
          </div>
          <div class="gp-row">
            <span class="gp-step cut-step">⚠ IF WRONG</span>
            <span class="gp-body gray">Either team scoring first collapses TIE price. Exit quickly after a goal.</span>
          </div>
        </div>"""

    def fmt_scenario(sc_data: dict, scorer_key: str) -> str:
        payout = sc_data["payout_usd"]
        roi = sc_data["roi"]
        color = "green" if roi > 0.05 else ("red" if roi < -0.05 else "gray")
        scorer_name = sig.team_a if scorer_key == "A" else sig.team_b
        roi_str = f"+{roi:.0%}" if roi > 0 else f"{roi:.0%}"
        return (
            f"<b>{scorer_name}</b> scores first "
            f"<span class='{color}'>${payout:.2f} ({roi_str})</span> "
            f"<span class='gray'>· {sc[f'p_{scorer_key}_scores_first']:.0%} chance</span>"
        )

    contract_desc = "YES pays $1 if this outcome happens" if sig.side == "yes" else "NO pays $1 if this does NOT happen"
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
          <div class="metrics-row">
            <div class="metric-cell">
              <div class="metric-label">CONTRACT</div>
              <div class="metric-big">{sig.outcome}</div>
              <div class="metric-sub">{contract_desc}</div>
            </div>
            <div class="metric-cell">
              <div class="metric-label">ENTRY PRICE</div>
              <div class="metric-big">{entry_c:.0f}¢</div>
              <div class="metric-sub">fair value: {sig.fair_prob:.1%}</div>
            </div>
            <div class="metric-cell">
              <div class="metric-label">CONTRACTS (${stake_usd:.0f})</div>
              <div class="metric-big">{sc["contracts"]}</div>
              <div class="metric-sub">cost ≈ ${cost_usd:.2f}</div>
            </div>
            <div class="metric-cell">
              <div class="metric-label">EDGE</div>
              <div class="metric-big green">+{sig.edge:.1%}</div>
              <div class="metric-sub">vs major books</div>
            </div>
            <div class="metric-cell">
              <div class="metric-label">EXPECTED VALUE</div>
              <div class="metric-big">${sc["expected_value_usd"]:.2f}</div>
              <div class="metric-sub">on ${stake_usd:.0f} entry</div>
            </div>
          </div>
          <div class="divider"></div>
          {game_plan_html}
          <div class="divider"></div>
          <div style="font-size:12px; color:#a8b4cc; margin-bottom:10px; font-weight:700; letter-spacing:0.05em;">
            📊 FIRST GOAL PRICE IMPACT
          </div>
          <div class="scenarios-row">
            <div class="scenario-block">
              {fmt_scenario(sc_a, "A")}
            </div>
            <div class="scenario-block">
              {fmt_scenario(sc_b, "B")}
            </div>
          </div>
          <div class="ticker-line">Ticker: {sig.kalshi_ticker}</div>
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
