#!/usr/bin/env python3
"""
Dexcom Sync - Simple CLI tool to sync Dexcom glucose readings to Nightscout
Similar to Tconnectsync architecture
"""

import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv
from dexcom_client import DexcomClient
from nightscout_connector import NightscoutConnector

# Load environment variables
load_dotenv()

# Setup logging
def setup_logging():
    """Configure logging with file rotation every 2 days"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'dexcom_sync.log'
    
    # Create logger
    logger = logging.getLogger('dexcom_sync')
    logger.setLevel(logging.INFO)
    
    # Format: [YYYY-MM-DD HH:MM:SS] LEVEL: Message
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)-8s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation every 2 days
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=2,
        backupCount=10  # Keep 10 backup files
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler for real-time output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

class DexcomSync:
    """Main sync manager"""
    
    def __init__(self):
        self.dexcom = DexcomClient()
        self.nightscout = None
        
        # Initialize Nightscout if configured
        ns_url = os.getenv('NIGHTSCOUT_URL')
        ns_token = os.getenv('NIGHTSCOUT_API_TOKEN')
        if ns_url and ns_token:
            self.nightscout = NightscoutConnector(ns_url, ns_token)
    
    def display_readings(self, readings: list):
        """Display the last N readings in a nice format"""
        if not readings:
            logger.info("No readings found.")
            return
        
        logger.info("=" * 60)
        logger.info("DEXCOM GLUCOSE READINGS")
        logger.info("=" * 60)
        
        for i, reading in enumerate(readings, 1):
            timestamp = reading['timestamp']
            value = reading['value']
            trend = reading['trend']
            
            # Format timestamp
            time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            # Calculate time ago
            now = datetime.now(timezone.utc)
            minutes_ago = int((now - timestamp).total_seconds() / 60)
            if minutes_ago < 1:
                time_ago = "Just now"
            elif minutes_ago == 1:
                time_ago = "1 minute ago"
            else:
                time_ago = f"{minutes_ago} minutes ago"
            
            logger.info(f"  {i}. {value:>3} mg/dL  [{trend:>12}]  {time_str}  ({time_ago})")
        
        logger.info("=" * 60)
    
    def sync(self, days: int = 0):
        """Sync Dexcom readings to configured destinations
        
        Args:
            days: Number of days to backfill (0 = default 2 hours, 1-30 = historical)
        """
        try:
            logger.info("Starting sync...")
            
            if not self.dexcom.is_authenticated():
                logger.info("Authenticating with Dexcom...")
                if not self.dexcom.login():
                    logger.error("Failed to authenticate with Dexcom")
                    logger.error("Please configure DEXCOM_EMAIL and DEXCOM_PASSWORD in .env")
                    return False
                logger.info("[OK] Successfully authenticated with Dexcom")
            
            logger.info("Fetching glucose readings...")
            
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            if days > 0:
                start_date = end_date - timedelta(days=days)
                logger.info(f"Backfilling {days} day(s) of data...")
            else:
                start_date = end_date - timedelta(hours=2)
            
            readings = self.dexcom.get_glucose_readings(
                start_date=start_date,
                end_date=end_date
            )
            
            if not readings:
                logger.warning("No readings found from Dexcom")
                return False
            
            logger.info(f"[OK] Retrieved {len(readings)} glucose readings")
            
            # Display last 5 readings
            self.display_readings(readings[-5:])
            
            # Push to Nightscout if configured
            if self.nightscout:
                logger.info("Pushing to Nightscout...")
                success_count = 0
                for reading in readings:
                    if self.nightscout.push_reading(reading):
                        success_count += 1
                logger.info(f"[OK] Pushed {success_count}/{len(readings)} readings to Nightscout")
            else:
                logger.debug("Nightscout not configured (set NIGHTSCOUT_URL and NIGHTSCOUT_API_TOKEN)")
            
            logger.info("[OK] Sync completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
            return False
    
    def run_continuous(self):
        """Run continuous syncing"""
        import time
        
        interval = int(os.getenv('SYNC_INTERVAL_MINUTES', '3')) * 60
        logger.info(f"Starting continuous sync every {os.getenv('SYNC_INTERVAL_MINUTES', '3')} minutes")
        logger.info("Press Ctrl+C to stop.\n")
        
        try:
            while True:
                self.sync()
                logger.info(f"Waiting {interval // 60} minutes until next sync...\n")
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("\nSync stopped by user")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dexcom Sync - Sync Dexcom readings to Nightscout')
    parser.add_argument(
        'action',
        nargs='?',
        default='once',
        choices=['once', 'continuous', 'config', 'backfill'],
        help='Action to perform (default: once)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help='Number of days to backfill (1-30, default: 1)'
    )
    
    args = parser.parse_args()
    
    sync = DexcomSync()
    
    if args.action == 'config':
        logger.info("Current Configuration:")
        logger.info(f"  DEXCOM_EMAIL: {os.getenv('DEXCOM_EMAIL', 'NOT SET')}")
        logger.info(f"  DEXCOM_PASSWORD: {'SET' if os.getenv('DEXCOM_PASSWORD') else 'NOT SET'}")
        logger.info(f"  DEXCOM_USE_INTL: {os.getenv('DEXCOM_USE_INTL', 'false')}")
        logger.info(f"  NIGHTSCOUT_URL: {os.getenv('NIGHTSCOUT_URL', 'NOT SET')}")
        logger.info(f"  NIGHTSCOUT_API_TOKEN: {'SET' if os.getenv('NIGHTSCOUT_API_TOKEN') else 'NOT SET'}")
        logger.info(f"  SYNC_INTERVAL_MINUTES: {os.getenv('SYNC_INTERVAL_MINUTES', '3')}")
        return
    
    if args.action == 'once':
        logger.info("Running one-time sync...")
        success = sync.sync(days=0)
        sys.exit(0 if success else 1)
    elif args.action == 'continuous':
        sync.run_continuous()
    elif args.action == 'backfill':
        # Validate days parameter
        if args.days < 1 or args.days > 30:
            logger.error("Days must be between 1 and 30")
            sys.exit(1)
        logger.info(f"Running backfill for {args.days} day(s)...")
        success = sync.sync(days=args.days)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

