#!/usr/bin/env python3
"""
Authentication Health Monitor
Provides real-time monitoring of token health and authentication status
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthMonitor:
    """Monitor authentication health and provide status reports"""

    def __init__(self):
        self.metrics_file = Path("backend/token_metrics.json")
        self.token_file = Path("backend/.schwab_tokens.json")
        self.alert_file = Path("backend/AUTH_ALERT.txt")
        self.status_file = Path("backend/auth_status.json")

    async def get_auth_health(self) -> Dict[str, Any]:
        """Get comprehensive authentication health status"""
        health = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "unknown",
            "token_status": {},
            "metrics": {},
            "alerts": [],
            "recommendations": []
        }

        # Check token status
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)

                expires_at = datetime.fromisoformat(token_data["expires_at"])
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)

                now = datetime.now(timezone.utc)
                hours_until_expiry = (expires_at - now).total_seconds() / 3600

                health["token_status"] = {
                    "exists": True,
                    "expires_at": expires_at.isoformat(),
                    "hours_until_expiry": round(hours_until_expiry, 2),
                    "refresh_count": token_data.get("refresh_count", 0),
                    "last_refresh": token_data.get("last_refresh")
                }

                # Determine overall status
                if hours_until_expiry < 0:
                    health["status"] = "expired"
                    health["alerts"].append("Token is expired!")
                    health["recommendations"].append("Run manual authentication immediately")
                elif hours_until_expiry < 1:
                    health["status"] = "critical"
                    health["alerts"].append(f"Token expires in {hours_until_expiry:.2f} hours")
                    health["recommendations"].append("Ensure auto-refresh is running")
                elif hours_until_expiry < 24:
                    health["status"] = "warning"
                    health["alerts"].append(f"Token expires in {hours_until_expiry:.1f} hours")
                else:
                    health["status"] = "healthy"

            except Exception as e:
                health["status"] = "error"
                health["alerts"].append(f"Failed to read token file: {e}")
        else:
            health["status"] = "no_token"
            health["alerts"].append("No token file found")
            health["recommendations"].append("Run manual authentication")

        # Check metrics
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    metrics = json.load(f)

                health["metrics"] = {
                    "total_refreshes": metrics.get("total_refreshes", 0),
                    "successful_refreshes": metrics.get("successful_refreshes", 0),
                    "failed_refreshes": metrics.get("failed_refreshes", 0),
                    "consecutive_failures": metrics.get("consecutive_failures", 0),
                    "uptime_percentage": metrics.get("uptime_percentage", 0),
                    "last_refresh_time": metrics.get("last_refresh_time"),
                    "last_failure_time": metrics.get("last_failure_time"),
                    "last_failure_reason": metrics.get("last_failure_reason")
                }

                # Add alerts based on metrics
                if metrics.get("consecutive_failures", 0) >= 3:
                    health["alerts"].append(f"High consecutive failures: {metrics['consecutive_failures']}")
                    health["recommendations"].append("Check network connectivity and API status")

                if metrics.get("uptime_percentage", 100) < 95:
                    health["alerts"].append(f"Low uptime: {metrics['uptime_percentage']:.1f}%")

            except Exception as e:
                logger.error(f"Failed to read metrics: {e}")

        # Check for alerts
        if self.alert_file.exists():
            try:
                with open(self.alert_file, 'r') as f:
                    alert_content = f.read()
                if alert_content:
                    health["alerts"].append("Manual authentication alert active!")
                    health["status"] = "critical"
            except:
                pass

        return health

    async def generate_status_report(self) -> str:
        """Generate human-readable status report"""
        health = await self.get_auth_health()

        report = []
        report.append("=" * 60)
        report.append("AUTHENTICATION STATUS REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {health['timestamp']}")
        report.append(f"Status: {health['status'].upper()}")
        report.append("")

        # Token status
        if health["token_status"]:
            report.append("TOKEN STATUS:")
            ts = health["token_status"]
            if ts.get("exists"):
                report.append(f"  Expires: {ts['expires_at']}")
                report.append(f"  Hours remaining: {ts['hours_until_expiry']}")
                report.append(f"  Refresh count: {ts['refresh_count']}")
                if ts.get("last_refresh"):
                    report.append(f"  Last refresh: {ts['last_refresh']}")
            else:
                report.append("  No token found")
        report.append("")

        # Metrics
        if health["metrics"]:
            report.append("REFRESH METRICS:")
            m = health["metrics"]
            report.append(f"  Total refreshes: {m['total_refreshes']}")
            report.append(f"  Successful: {m['successful_refreshes']}")
            report.append(f"  Failed: {m['failed_refreshes']}")
            report.append(f"  Consecutive failures: {m['consecutive_failures']}")
            report.append(f"  Uptime: {m['uptime_percentage']:.1f}%")
            if m.get("last_failure_time"):
                report.append(f"  Last failure: {m['last_failure_time']}")
                if m.get("last_failure_reason"):
                    report.append(f"  Reason: {m['last_failure_reason'][:100]}")
        report.append("")

        # Alerts
        if health["alerts"]:
            report.append("ALERTS:")
            for alert in health["alerts"]:
                report.append(f"  ⚠️  {alert}")
            report.append("")

        # Recommendations
        if health["recommendations"]:
            report.append("RECOMMENDATIONS:")
            for rec in health["recommendations"]:
                report.append(f"  → {rec}")
            report.append("")

        report.append("=" * 60)

        return "\n".join(report)

    async def save_status(self):
        """Save current status to file"""
        try:
            health = await self.get_auth_health()
            with open(self.status_file, 'w') as f:
                json.dump(health, f, indent=2)
            logger.info("Status saved to auth_status.json")
        except Exception as e:
            logger.error(f"Failed to save status: {e}")

    async def monitor_loop(self, interval_seconds: int = 60):
        """Continuous monitoring loop"""
        logger.info("Starting authentication monitor")

        while True:
            try:
                health = await self.get_auth_health()

                # Log based on status
                if health["status"] == "healthy":
                    logger.info(f"Auth healthy, token expires in {health['token_status'].get('hours_until_expiry', 'unknown')} hours")
                elif health["status"] in ["warning", "critical"]:
                    logger.warning(f"Auth {health['status']}: {', '.join(health['alerts'])}")
                elif health["status"] in ["expired", "no_token", "error"]:
                    logger.error(f"Auth {health['status']}: {', '.join(health['alerts'])}")

                # Save status
                await self.save_status()

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(interval_seconds)


async def main():
    """Run authentication monitor"""
    monitor = AuthMonitor()

    # Print current status
    print(await monitor.generate_status_report())

    # Start monitoring
    await monitor.monitor_loop()


if __name__ == "__main__":
    asyncio.run(main())