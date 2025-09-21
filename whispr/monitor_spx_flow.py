#!/usr/bin/env python3
"""Real-time SPX data flow monitor"""
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/whispr.db")

def monitor_spx_data():
    """Monitor SPX data flowing into database"""
    print("\n🎯 SPX DATA FLOW MONITOR")
    print("=" * 60)

    last_count = 0

    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Get latest data
            cursor.execute("""
                SELECT COUNT(*) as total,
                       MAX(timestamp) as latest_time,
                       MAX(price) as latest_price
                FROM spx_price_ticks
                WHERE DATE(timestamp) = DATE('now')
            """)

            total, latest_time, latest_price = cursor.fetchone()

            if total and total > last_count:
                print(f"\n✅ NEW DATA: {datetime.now().strftime('%H:%M:%S')}")
                print(f"   Total records today: {total}")
                print(f"   Latest price: ${latest_price:.2f}" if latest_price else "   Latest price: N/A")
                print(f"   Latest timestamp: {latest_time}")

                # Get last 5 prices
                cursor.execute("""
                    SELECT timestamp, price, high, low, volume
                    FROM spx_price_ticks
                    ORDER BY timestamp DESC
                    LIMIT 5
                """)

                records = cursor.fetchall()
                if records:
                    print("\n   Recent ticks:")
                    for ts, price, high, low, vol in records:
                        print(f"   {ts[-15:]} | ${price:.2f} | H:${high:.2f} L:${low:.2f} | Vol:{vol:,}")

                last_count = total
            else:
                print(f"\r⏳ Monitoring... Records: {total or 0} | Last check: {datetime.now().strftime('%H:%M:%S')}", end="", flush=True)

            conn.close()
            time.sleep(5)  # Check every 5 seconds

        except KeyboardInterrupt:
            print("\n\n🛑 Monitor stopped")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_spx_data()