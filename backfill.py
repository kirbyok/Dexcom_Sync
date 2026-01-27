#!/usr/bin/env python3
"""
Backfill helper to sync the last N hours from Dexcom (CGM) and/or Tandem (pump) to Nightscout.

Usage examples:
  python backfill.py --source both --hours 24
  python backfill.py --source dexcom --hours 24
  python backfill.py --source tandem --hours 24
"""

import math
import argparse
import logging
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Load environment variables from explicit path
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from main import DexcomSync  # noqa: E402
from tandem_main import TandemSync  # noqa: E402

logger = logging.getLogger("backfill")
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)-8s: %(message)s')


def backfill_dexcom(hours: int) -> bool:
    # DexcomSync.sync accepts days; convert hours→days (ceil)
    days = max(1, math.ceil(hours / 24))
    logger.info("Starting Dexcom backfill for ~%s hour(s) (days=%s)", hours, days)
    return DexcomSync().sync(days=days)


def backfill_tandem(hours: int) -> bool:
    logger.info("Starting Tandem backfill for %s hour(s)", hours)
    sync = TandemSync()
    return sync.sync(hours=hours)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill last N hours from Dexcom and/or Tandem")
    parser.add_argument(
        "--source",
        choices=["both", "dexcom", "tandem"],
        default="both",
        help="Select which source(s) to backfill",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours to backfill (default: 24)",
    )
    args = parser.parse_args()

    ok_results: List[bool] = []

    if args.source in ("both", "dexcom"):
        ok_results.append(backfill_dexcom(args.hours))
    if args.source in ("both", "tandem"):
        ok_results.append(backfill_tandem(args.hours))

    if all(ok_results):
        logger.info("Backfill completed successfully")
    else:
        logger.warning("Backfill finished with some errors; check logs above")


if __name__ == "__main__":
    main()
