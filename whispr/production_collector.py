#!/usr/bin/env python3
"""
Production SPX Data Collector
Integrates with TokenManager for continuous operation without auth interruptions
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from datetime import datetime, timezone
import logging
import signal
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend/production_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionSPXCollector:
    """Production-grade SPX data collector with automatic auth management"""

    def __init__(self):
        self.token_manager = None
        self.collector = None
        self.running = False

        # Statistics
        self.stats = {
            "start_time": None,
            "tick_count": 0,
            "error_count": 0,
            "reconnect_count": 0,
            "last_tick_time": None,
            "last_error_time": None
        }

        # Configuration
        self.max_reconnect_attempts = 10
        self.reconnect_delay_seconds = 30

    async def initialize(self) -> bool:
        """Initialize collector with TokenManager"""
        try:
            logger.info("="*60)
            logger.info("PRODUCTION SPX COLLECTOR")
            logger.info("="*60)

            # Import and initialize TokenManager
            from token_manager import get_token_manager
            self.token_manager = get_token_manager()

            # Initialize token manager
            if not await self.token_manager.initialize():
                logger.error("TokenManager initialization failed")
                return False

            # Start auto-refresh
            await self.token_manager.start_auto_refresh()
            logger.info("Token auto-refresh started")

            # Get initial token
            token = await self.token_manager.ensure_valid_token()
            if not token:
                logger.error("No valid token available")
                return False

            # Initialize data collector
            if not await self._initialize_collector():
                return False

            self.stats["start_time"] = datetime.now(timezone.utc)
            logger.info("✅ Production collector initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    async def _initialize_collector(self) -> bool:
        """Initialize Schwab data collector with current tokens"""
        try:
            from data_collector import SchwabDataCollector
            from schwab_config import SchwabOAuthManager

            # Create OAuth manager with TokenManager's tokens
            oauth = SchwabOAuthManager(
                self.token_manager.config['client_id'],
                self.token_manager.config['client_secret'],
                self.token_manager.config['redirect_uri']
            )

            # Set tokens from TokenManager
            if self.token_manager.token:
                from schwab_config import SchwabTokens
                oauth.tokens = SchwabTokens(
                    access_token=self.token_manager.token.access_token,
                    refresh_token=self.token_manager.token.refresh_token,
                    expires_at=self.token_manager.token.expires_at,
                    token_type=self.token_manager.token.token_type,
                    scope=self.token_manager.token.scope
                )
                oauth.token_file = "backend/.schwab_tokens.json"

                # Create data collector
                self.collector = SchwabDataCollector(oauth)

                # Connect to API
                connected = await self.collector.connect()
                if not connected:
                    logger.warning("Collector connection not confirmed")
                    # Continue anyway as it might still work

                logger.info("Data collector initialized")
                return True
            else:
                logger.error("No tokens available from TokenManager")
                return False

        except Exception as e:
            logger.error(f"Collector initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def process_tick(self, tick):
        """Process incoming market tick"""
        try:
            self.stats["tick_count"] += 1
            self.stats["last_tick_time"] = datetime.now(timezone.utc)

            # Log periodically
            if self.stats["tick_count"] % 100 == 1:
                logger.info(f"Tick #{self.stats['tick_count']}: ${tick.price:.2f} @ {tick.timestamp.strftime('%H:%M:%S')}")

            # Store in database
            from database import log_spx_tick
            await log_spx_tick(
                price=tick.price,
                high=tick.high,
                low=tick.low,
                volume=tick.volume,
                timestamp=tick.timestamp.isoformat()
            )

        except Exception as e:
            self.stats["error_count"] += 1
            self.stats["last_error_time"] = datetime.now(timezone.utc)
            logger.error(f"Error processing tick: {e}")

    async def collect_loop(self):
        """Main collection loop with automatic reconnection"""
        reconnect_attempts = 0

        while self.running:
            try:
                # Ensure we have a valid token
                token = await self.token_manager.ensure_valid_token()
                if not token:
                    logger.error("No valid token available, waiting...")
                    await asyncio.sleep(self.reconnect_delay_seconds)
                    continue

                # Re-initialize collector if needed
                if not self.collector or not self.collector.connected:
                    logger.info("Re-initializing collector...")
                    if not await self._initialize_collector():
                        reconnect_attempts += 1
                        if reconnect_attempts >= self.max_reconnect_attempts:
                            logger.error(f"Max reconnect attempts ({self.max_reconnect_attempts}) reached")
                            break

                        delay = self.reconnect_delay_seconds * reconnect_attempts
                        logger.info(f"Reconnect attempt {reconnect_attempts}/{self.max_reconnect_attempts} in {delay}s")
                        await asyncio.sleep(delay)
                        continue

                    self.stats["reconnect_count"] += 1
                    reconnect_attempts = 0  # Reset on successful reconnect

                # Get current quote
                logger.info("Fetching current SPX quote...")
                quote = await self.collector.get_current_spx_quote()
                if quote:
                    logger.info(f"SPX Quote: ${quote.get('price', 'N/A')} "
                              f"(High: ${quote.get('high', 'N/A')}, Low: ${quote.get('low', 'N/A')})")

                    # Store quote
                    from database import log_spx_tick
                    await log_spx_tick(
                        price=quote.get('price', 0),
                        high=quote.get('high', 0),
                        low=quote.get('low', 0),
                        volume=quote.get('volume', 0),
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                    self.stats["tick_count"] += 1
                    self.stats["last_tick_time"] = datetime.now(timezone.utc)

                # Stream ticks
                logger.info("Starting live stream...")
                await self.collector.stream_spx_ticks(callback=self.process_tick)

            except asyncio.CancelledError:
                logger.info("Collection cancelled")
                break
            except Exception as e:
                self.stats["error_count"] += 1
                self.stats["last_error_time"] = datetime.now(timezone.utc)
                logger.error(f"Collection error: {e}")

                reconnect_attempts += 1
                if reconnect_attempts >= self.max_reconnect_attempts:
                    logger.error(f"Max reconnect attempts reached, stopping")
                    break

                delay = self.reconnect_delay_seconds * reconnect_attempts
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

    async def health_monitor_loop(self):
        """Monitor collector health and log statistics"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute

                # Get token status
                token_status = await self.token_manager.get_status()

                # Calculate uptime
                if self.stats["start_time"]:
                    uptime = datetime.now(timezone.utc) - self.stats["start_time"]
                    uptime_hours = uptime.total_seconds() / 3600
                else:
                    uptime_hours = 0

                # Check for stale data
                stale_warning = ""
                if self.stats["last_tick_time"]:
                    time_since_tick = (datetime.now(timezone.utc) - self.stats["last_tick_time"]).total_seconds()
                    if time_since_tick > 300:  # 5 minutes
                        stale_warning = f" ⚠️  No ticks for {time_since_tick/60:.1f} minutes"

                # Log health status
                logger.info(f"Health: Uptime {uptime_hours:.1f}h, "
                          f"Ticks: {self.stats['tick_count']}, "
                          f"Errors: {self.stats['error_count']}, "
                          f"Reconnects: {self.stats['reconnect_count']}, "
                          f"Token: {token_status['health']}{stale_warning}")

                # Check database
                import aiosqlite
                async with aiosqlite.connect('data/whispr.db') as conn:
                    cursor = await conn.execute(
                        "SELECT COUNT(*) FROM spx_price_ticks WHERE date(timestamp) = date('now')"
                    )
                    db_count = (await cursor.fetchone())[0]
                    logger.info(f"Database ticks today: {db_count}")

            except Exception as e:
                logger.error(f"Health monitor error: {e}")

    async def run(self):
        """Main runner"""
        self.running = True

        # Initialize
        if not await self.initialize():
            logger.error("Failed to initialize, exiting")
            return

        # Create tasks
        collect_task = asyncio.create_task(self.collect_loop())
        health_task = asyncio.create_task(self.health_monitor_loop())

        # Set up callbacks for token events
        async def on_refresh_success(token):
            logger.info(f"Token refreshed successfully, expires at {token.expires_at}")

        async def on_refresh_failure(error):
            logger.error(f"Token refresh failed: {error}")

        async def on_manual_auth_needed(reason):
            logger.critical(f"MANUAL AUTH REQUIRED: {reason}")
            logger.critical("Run: python3 manual_auth_final.py")

        self.token_manager.on_refresh_success = on_refresh_success
        self.token_manager.on_refresh_failure = on_refresh_failure
        self.token_manager.on_manual_auth_needed = on_manual_auth_needed

        try:
            # Wait for tasks
            await asyncio.gather(collect_task, health_task)
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            self.running = False

            # Stop token manager
            await self.token_manager.stop_auto_refresh()

            # Cancel tasks
            collect_task.cancel()
            health_task.cancel()

            try:
                await collect_task
                await health_task
            except asyncio.CancelledError:
                pass

            # Final statistics
            logger.info("="*60)
            logger.info("FINAL STATISTICS")
            logger.info("="*60)
            if self.stats["start_time"]:
                uptime = datetime.now(timezone.utc) - self.stats["start_time"]
                logger.info(f"Total uptime: {uptime}")
            logger.info(f"Total ticks: {self.stats['tick_count']}")
            logger.info(f"Total errors: {self.stats['error_count']}")
            logger.info(f"Total reconnects: {self.stats['reconnect_count']}")

            # Token statistics
            token_status = await self.token_manager.get_status()
            if token_status.get("metrics"):
                metrics = token_status["metrics"]
                logger.info(f"Token refreshes: {metrics.get('successful_refreshes', 0)}/{metrics.get('total_refreshes', 0)}")
                logger.info(f"Token uptime: {metrics.get('uptime_percentage', 0):.1f}%")


def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    sys.exit(0)


async def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run collector
    collector = ProductionSPXCollector()
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())