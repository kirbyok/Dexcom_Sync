#!/usr/bin/env python3
"""
Backfill helper to sync the last N hours from Dexcom (CGM) to Nightscout.

Usage examples:
  python backfill.py --hours 24
"""

import math
import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from explicit path
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from main import DexcomSync  # noqa: E402

logger = logging.getLogger("backfill")
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)-8s: %(message)s')


def backfill_dexcom(hours: int) -> bool:
    # DexcomSync.sync accepts days; convert hours→days (ceil)
    days = max(1, math.ceil(hours / 24))
    logger.info("Starting Dexcom backfill for ~%s hour(s) (days=%s)", hours, days)
    return DexcomSync().sync(days=days)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill last N hours from Dexcom")
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours to backfill (default: 24)",
    )
    args = parser.parse_args()

    if backfill_dexcom(args.hours):
        logger.info("Backfill completed successfully")
    else:
        logger.warning("Backfill finished with errors; check logs above")


if __name__ == "__main__":
    main()
