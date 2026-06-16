#!/usr/bin/env python3
"""
Kalshi World Cup Arbitrage Bot
Usage:
  python main.py           # dry run (no real orders)
  python main.py --live    # real money mode
  python main.py --once    # run once and exit
  python main.py --interval 10   # scan every 10 minutes (default 15)
"""
import argparse
import schedule
import time
from src.strategy import Strategy
from src.executor import Executor
from src.risk import RiskManager
from src.logger import log


def run_cycle(strategy: Strategy, executor: Executor):
    log.info("=" * 60)
    try:
        signals = strategy.scan()
        executor.execute_signals(signals)
    except Exception as e:
        log.error(f"Cycle error: {e}", exc_info=True)


def main():
    parser = argparse.ArgumentParser(description="Kalshi WC arbitrage bot")
    parser.add_argument("--live", action="store_true", help="Enable real order placement")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=15, help="Scan interval in minutes (default 15)")
    args = parser.parse_args()

    if args.live:
        log.warning("LIVE MODE — real orders will be placed!")
        confirm = input("Type YES to confirm: ")
        if confirm.strip() != "YES":
            log.info("Aborted.")
            return

    risk = RiskManager()
    strategy = Strategy()
    executor = Executor(risk=risk, dry_run=not args.live)

    if args.once:
        run_cycle(strategy, executor)
        return

    log.info(f"Scheduler started — scanning every {args.interval} minutes")
    run_cycle(strategy, executor)
    schedule.every(args.interval).minutes.do(run_cycle, strategy, executor)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
