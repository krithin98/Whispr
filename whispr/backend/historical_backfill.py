#!/usr/bin/env python3
"""
Historical Data Backfill Script
Populates database with 20 years of historical data from Schwab API
"""

import asyncio
import sqlite3
import os
from datetime import datetime, timezone
from typing import List, Dict, Any
from data_collector import SchwabDataCollector
from schwab_config import SchwabOAuthManager

class HistoricalDataBackfill:
    """Manages comprehensive historical data backfill from Schwab API"""
    
    def __init__(self, db_path: str = "/opt/spx-atr/data/spx_tracking.db"):
        self.db_path = db_path
        self.oauth_manager = None
        self.collector = None
        
    async def initialize(self):
        """Initialize Schwab API connection"""
        print("🔧 Initializing Schwab API connection...")
        
        # Set environment variables
        os.environ['SCHWAB_CLIENT_ID'] = 'aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1'
        os.environ['SCHWAB_CLIENT_SECRET'] = '0dG11fLY8qF7iYz3'
        os.environ['SCHWAB_REDIRECT_URI'] = 'https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
        
        self.oauth_manager = SchwabOAuthManager(
            client_id='aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1',
            client_secret='0dG11fLY8qF7iYz3',
            redirect_uri='https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback'
        )
        
        self.collector = SchwabDataCollector(self.oauth_manager)
        print("✅ Schwab API connection initialized")
        
    def create_historical_tables(self):
        """Create tables specifically for historical data storage"""
        print("🔧 Creating historical data tables...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Historical candles table - stores all timeframes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historical_candles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                open_price REAL NOT NULL,
                high_price REAL NOT NULL,
                low_price REAL NOT NULL,
                close_price REAL NOT NULL,
                volume INTEGER NOT NULL,
                source TEXT DEFAULT 'schwab_api',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timeframe, timestamp)
            )
        """)
        
        # Index for fast queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_historical_symbol_timeframe_time 
            ON historical_candles(symbol, timeframe, timestamp)
        """)
        
        conn.commit()
        conn.close()
        print("✅ Historical data tables created")
        
    async def fetch_and_store_timeframe(self, timeframe_name: str, params: Dict[str, Any]) -> int:
        """Fetch data for a specific timeframe and store in database"""
        print(f"📊 Fetching {timeframe_name} data...")
        
        try:
            # Add symbol to params
            params_with_symbol = {
                "symbol": "$SPX",
                "needExtendedHoursData": "false",
                **params
            }
            
            # Fetch from Schwab API
            response = await self.collector._make_api_request(
                "/marketdata/v1/pricehistory", 
                params_with_symbol
            )
            
            if "candles" not in response or not response["candles"]:
                print(f"❌ No {timeframe_name} data received")
                return 0
                
            candles = response["candles"]
            print(f"✅ Received {len(candles)} {timeframe_name} candles")
            
            # Store in database
            stored_count = self._store_candles(candles, timeframe_name)
            print(f"✅ Stored {stored_count} {timeframe_name} candles in database")
            
            return stored_count
            
        except Exception as e:
            print(f"❌ Error fetching {timeframe_name} data: {e}")
            return 0
            
    def _store_candles(self, candles: List[Dict], timeframe: str) -> int:
        """Store candles in database"""
        try:
            conn = sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            print(f"❌ Failed to connect to database at {self.db_path}: {e}")
            return 0

        cursor = conn.cursor()
        before_changes = conn.total_changes

        for candle in candles:
            timestamp = "unknown"
            try:
                # Convert timestamp
                timestamp = datetime.fromtimestamp(
                    candle["datetime"] / 1000,
                    timezone.utc
                ).isoformat()

                # Insert candle (ignore duplicates)
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO historical_candles
                    (symbol, timeframe, timestamp, open_price, high_price, low_price, close_price, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "SPX",
                        timeframe,
                        timestamp,
                        candle["open"],
                        candle["high"],
                        candle["low"],
                        candle["close"],
                        candle.get("volume", 0)
                    ),
                )
            except sqlite3.IntegrityError as e:
                print(f"⚠️ Unique constraint error for {timestamp}: {e}")
            except Exception as e:
                print(f"⚠️ Error storing candle {timestamp}: {e}")

        conn.commit()
        stored_count = conn.total_changes - before_changes
        conn.close()

        return stored_count
        
    async def run_full_backfill(self):
        """Run comprehensive historical data backfill"""
        print("🚀 Starting Full Historical Data Backfill...")
        print("=" * 60)
        
        # Initialize
        await self.initialize()
        self.create_historical_tables()
        
        # Define backfill targets
        backfill_tasks = [
            # Long-term data (20 years)
            ("daily_20y", {"periodType": "year", "period": 20, "frequencyType": "daily", "frequency": 1}),
            ("weekly_20y", {"periodType": "year", "period": 20, "frequencyType": "weekly", "frequency": 1}),
            ("monthly_20y", {"periodType": "year", "period": 20, "frequencyType": "monthly", "frequency": 1}),
            
            # Intraday data (10 days max)
            ("1min_10d", {"periodType": "day", "period": 10, "frequencyType": "minute", "frequency": 1}),
            ("10min_10d", {"periodType": "day", "period": 10, "frequencyType": "minute", "frequency": 10}),
            ("15min_10d", {"periodType": "day", "period": 10, "frequencyType": "minute", "frequency": 15}),
            ("30min_10d", {"periodType": "day", "period": 10, "frequencyType": "minute", "frequency": 30}),
        ]
        
        total_stored = 0
        
        # Execute backfill tasks
        for timeframe_name, params in backfill_tasks:
            stored = await self.fetch_and_store_timeframe(timeframe_name, params)
            total_stored += stored
            print()  # Add spacing
            
        print("=" * 60)
        print(f"🎉 Backfill Complete! Total candles stored: {total_stored:,}")
        
        # Summary report
        self._generate_summary_report()
        
    def _generate_summary_report(self):
        """Generate summary of stored historical data"""
        print("\n📊 Historical Data Summary:")
        print("-" * 40)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timeframe, COUNT(*) as count,
                   MIN(timestamp) as first_date,
                   MAX(timestamp) as last_date
            FROM historical_candles 
            GROUP BY timeframe 
            ORDER BY timeframe
        """)
        
        results = cursor.fetchall()
        
        for timeframe, count, first_date, last_date in results:
            print(f"📈 {timeframe}: {count:,} candles")
            print(f"   Range: {first_date[:10]} to {last_date[:10]}")
            
        conn.close()

async def main():
    """Main execution function"""
    backfill = HistoricalDataBackfill()
    await backfill.run_full_backfill()

if __name__ == "__main__":
    print("🚀 SPX Historical Data Backfill")
    print("=" * 60)
    asyncio.run(main())
