#!/usr/bin/env python3
"""
Production-Grade Token Manager
Ensures continuous API access with automatic token refresh and comprehensive monitoring
"""

import asyncio
import json
import os
import logging
import aiohttp
import aiofiles
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import base64
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend/token_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TokenStatus(Enum):
    """Token health status levels"""
    HEALTHY = "healthy"
    NEEDS_REFRESH = "needs_refresh"
    REFRESHING = "refreshing"
    EXPIRED = "expired"
    FAILED = "failed"
    NO_TOKEN = "no_token"

@dataclass
class TokenMetrics:
    """Token health metrics"""
    total_refreshes: int = 0
    successful_refreshes: int = 0
    failed_refreshes: int = 0
    consecutive_failures: int = 0
    last_refresh_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    last_failure_reason: Optional[str] = None
    average_refresh_duration_ms: float = 0.0
    uptime_percentage: float = 100.0

@dataclass
class ManagedToken:
    """Enhanced token with metadata"""
    access_token: str
    refresh_token: str
    expires_at: datetime
    token_type: str = "Bearer"
    scope: str = "api"
    obtained_at: Optional[datetime] = None
    refresh_count: int = 0
    last_refresh: Optional[datetime] = None
    next_refresh_scheduled: Optional[datetime] = None
    health_status: TokenStatus = TokenStatus.HEALTHY

class TokenManager:
    """
    Production-grade token manager with automatic refresh and monitoring
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize token manager with configuration"""
        self.config = self._load_config(config)

        # File paths
        self.token_file = Path(self.config.get("token_file", "backend/.schwab_tokens.json"))
        self.backup_dir = Path(self.config.get("backup_dir", "backend/token_backups"))
        self.metrics_file = Path("backend/token_metrics.json")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Token state
        self.token: Optional[ManagedToken] = None
        self.metrics = TokenMetrics()
        self.status = TokenStatus.NO_TOKEN

        # Refresh configuration
        self.refresh_before_expiry_hours = self.config.get("refresh_before_expiry_hours", 24)
        self.refresh_check_interval_minutes = self.config.get("refresh_check_interval_minutes", 30)
        self.max_retry_attempts = self.config.get("max_retry_attempts", 5)
        self.retry_delay_seconds = self.config.get("retry_delay_seconds", 60)

        # Tasks and locks
        self.refresh_task: Optional[asyncio.Task] = None
        self.monitor_task: Optional[asyncio.Task] = None
        self.refresh_lock = asyncio.Lock()
        self.running = False

        # Callbacks
        self.on_refresh_success: Optional[Callable] = None
        self.on_refresh_failure: Optional[Callable] = None
        self.on_manual_auth_needed: Optional[Callable] = None

        # Schwab API configuration
        self.base_url = "https://api.schwabapi.com"
        self.token_url = f"{self.base_url}/v1/oauth/token"

        logger.info("TokenManager initialized")

    def _load_config(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        default_config = {
            "client_id": "aovZp4jBkjJCvrvci7NOrM6yuZk6GIj1",
            "client_secret": "0dG11fLY8qF7iYz3",
            "redirect_uri": "https://whispr-jjygd8lca-krithins-projects-859494f2.vercel.app/auth/callback",
            "token_file": "backend/.schwab_tokens.json",
            "backup_dir": "backend/token_backups",
            "refresh_before_expiry_hours": 24,
            "refresh_check_interval_minutes": 30,
            "max_retry_attempts": 5,
            "retry_delay_seconds": 60,
            "alert_webhook_url": None,
            "alert_email": None
        }

        # Try to load from config file
        config_file = Path("backend/token_manager_config.json")
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")

        # Override with provided config
        if config:
            default_config.update(config)

        return default_config

    async def initialize(self) -> bool:
        """Initialize token manager and load existing tokens"""
        try:
            # Load existing tokens
            if await self.load_tokens():
                logger.info("Existing tokens loaded successfully")
                self.status = TokenStatus.HEALTHY

                # Load metrics
                await self._load_metrics()

                return True
            else:
                logger.warning("No existing tokens found")
                self.status = TokenStatus.NO_TOKEN
                return False

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            self.status = TokenStatus.FAILED
            return False

    async def load_tokens(self) -> bool:
        """Load tokens from file"""
        try:
            if not self.token_file.exists():
                logger.info("Token file not found")
                return False

            async with aiofiles.open(self.token_file, 'r') as f:
                data = json.loads(await f.read())

            # Parse token with timezone handling
            expires_at = datetime.fromisoformat(data["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            self.token = ManagedToken(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                expires_at=expires_at,
                token_type=data.get("token_type", "Bearer"),
                scope=data.get("scope", "api"),
                obtained_at=datetime.fromisoformat(data["obtained_at"]) if "obtained_at" in data else None,
                refresh_count=data.get("refresh_count", 0),
                last_refresh=datetime.fromisoformat(data["last_refresh"]) if "last_refresh" in data else None
            )

            # Update status based on expiration
            await self._update_token_status()

            logger.info(f"Tokens loaded, expires at {self.token.expires_at}")
            return True

        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
            return False

    async def save_tokens(self, create_backup: bool = True) -> bool:
        """Save tokens to file with optional backup"""
        try:
            if not self.token:
                return False

            # Prepare token data
            token_data = {
                "access_token": self.token.access_token,
                "refresh_token": self.token.refresh_token,
                "expires_at": self.token.expires_at.isoformat(),
                "token_type": self.token.token_type,
                "scope": self.token.scope,
                "obtained_at": self.token.obtained_at.isoformat() if self.token.obtained_at else datetime.now(timezone.utc).isoformat(),
                "refresh_count": self.token.refresh_count,
                "last_refresh": self.token.last_refresh.isoformat() if self.token.last_refresh else None,
                "next_refresh_scheduled": self.token.next_refresh_scheduled.isoformat() if self.token.next_refresh_scheduled else None
            }

            # Create backup if requested
            if create_backup:
                backup_file = self.backup_dir / f"tokens_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                async with aiofiles.open(backup_file, 'w') as f:
                    await f.write(json.dumps(token_data, indent=2))
                logger.debug(f"Token backup created: {backup_file}")

            # Save main token file
            async with aiofiles.open(self.token_file, 'w') as f:
                await f.write(json.dumps(token_data, indent=2))

            logger.info("Tokens saved successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
            return False

    async def refresh_tokens(self) -> bool:
        """Refresh access token using refresh token"""
        async with self.refresh_lock:
            if not self.token or not self.token.refresh_token:
                logger.error("No refresh token available")
                await self._alert_manual_auth_needed("No refresh token available")
                return False

            self.status = TokenStatus.REFRESHING
            start_time = datetime.now(timezone.utc)

            try:
                logger.info("Starting token refresh...")

                # Prepare request
                auth = base64.b64encode(f"{self.config['client_id']}:{self.config['client_secret']}".encode()).decode()
                headers = {
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                data = {
                    "grant_type": "refresh_token",
                    "refresh_token": self.token.refresh_token
                }

                # Create SSL context
                import ssl
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                # Make request
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                timeout = aiohttp.ClientTimeout(total=30)

                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    async with session.post(self.token_url, headers=headers, data=data) as response:
                        response_text = await response.text()

                        if response.status == 200:
                            token_data = json.loads(response_text)

                            # Update token
                            expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])
                            self.token = ManagedToken(
                                access_token=token_data["access_token"],
                                refresh_token=token_data["refresh_token"],
                                expires_at=expires_at,
                                token_type=token_data["token_type"],
                                scope=token_data["scope"],
                                obtained_at=self.token.obtained_at or datetime.now(timezone.utc),
                                refresh_count=self.token.refresh_count + 1,
                                last_refresh=datetime.now(timezone.utc),
                                next_refresh_scheduled=expires_at - timedelta(hours=self.refresh_before_expiry_hours)
                            )

                            # Save immediately
                            await self.save_tokens(create_backup=True)

                            # Update metrics
                            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                            await self._update_metrics_success(duration_ms)

                            self.status = TokenStatus.HEALTHY
                            logger.info(f"Token refresh successful! New expiry: {expires_at}")

                            # Trigger success callback
                            if self.on_refresh_success:
                                await self.on_refresh_success(self.token)

                            return True

                        else:
                            error_msg = f"HTTP {response.status}: {response_text}"
                            logger.error(f"Token refresh failed: {error_msg}")
                            await self._update_metrics_failure(error_msg)

                            # Check if manual auth needed
                            if "invalid_grant" in response_text or "expired" in response_text:
                                await self._alert_manual_auth_needed(error_msg)

                            return False

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Token refresh exception: {error_msg}")
                await self._update_metrics_failure(error_msg)

                # Trigger failure callback
                if self.on_refresh_failure:
                    await self.on_refresh_failure(error_msg)

                return False

            finally:
                if self.status == TokenStatus.REFRESHING:
                    await self._update_token_status()

    async def ensure_valid_token(self) -> Optional[str]:
        """Ensure we have a valid access token, refreshing if necessary"""
        if not self.token:
            if not await self.load_tokens():
                logger.error("No tokens available")
                return None

        # Check expiration
        now = datetime.now(timezone.utc)
        expires_at = self.token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        time_until_expiry = expires_at - now
        hours_until_expiry = time_until_expiry.total_seconds() / 3600

        logger.debug(f"Token expires in {hours_until_expiry:.1f} hours")

        # Refresh if needed
        if hours_until_expiry < self.refresh_before_expiry_hours:
            logger.info(f"Token expiring soon ({hours_until_expiry:.1f}h < {self.refresh_before_expiry_hours}h), refreshing...")

            # Try refresh with retries
            for attempt in range(self.max_retry_attempts):
                if await self.refresh_tokens():
                    return self.token.access_token

                if attempt < self.max_retry_attempts - 1:
                    delay = self.retry_delay_seconds * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retry attempt {attempt + 1}/{self.max_retry_attempts} in {delay}s")
                    await asyncio.sleep(delay)

            logger.error("All refresh attempts failed")
            return None

        return self.token.access_token

    async def start_auto_refresh(self):
        """Start automatic token refresh background task"""
        if self.refresh_task and not self.refresh_task.done():
            logger.warning("Auto-refresh already running")
            return

        self.running = True
        self.refresh_task = asyncio.create_task(self._refresh_loop())
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Auto-refresh started")

    async def stop_auto_refresh(self):
        """Stop automatic token refresh"""
        self.running = False

        if self.refresh_task:
            self.refresh_task.cancel()
            try:
                await self.refresh_task
            except asyncio.CancelledError:
                pass

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Auto-refresh stopped")

    async def _refresh_loop(self):
        """Background loop for automatic token refresh"""
        while self.running:
            try:
                # Ensure valid token
                token = await self.ensure_valid_token()

                if not token:
                    logger.error("Failed to maintain valid token")
                    await asyncio.sleep(self.retry_delay_seconds)
                else:
                    # Schedule next check
                    check_interval = self.refresh_check_interval_minutes * 60
                    logger.debug(f"Next token check in {check_interval/60:.1f} minutes")
                    await asyncio.sleep(check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Refresh loop error: {e}")
                await asyncio.sleep(self.retry_delay_seconds)

    async def _monitor_loop(self):
        """Background loop for monitoring token health"""
        while self.running:
            try:
                await self._update_token_status()
                await self._save_metrics()

                # Log health status periodically
                if self.token:
                    now = datetime.now(timezone.utc)
                    expires_at = self.token.expires_at
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)

                    hours_left = (expires_at - now).total_seconds() / 3600
                    logger.info(f"Token health: {self.status.value}, expires in {hours_left:.1f}h, "
                              f"refreshes: {self.metrics.successful_refreshes}/{self.metrics.total_refreshes}")

                await asyncio.sleep(300)  # Check every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(60)

    async def _update_token_status(self):
        """Update token health status"""
        if not self.token:
            self.status = TokenStatus.NO_TOKEN
            return

        now = datetime.now(timezone.utc)
        expires_at = self.token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        time_until_expiry = expires_at - now
        hours_until_expiry = time_until_expiry.total_seconds() / 3600

        if hours_until_expiry <= 0:
            self.status = TokenStatus.EXPIRED
        elif hours_until_expiry < self.refresh_before_expiry_hours:
            self.status = TokenStatus.NEEDS_REFRESH
        else:
            self.status = TokenStatus.HEALTHY

    async def _update_metrics_success(self, duration_ms: float):
        """Update metrics after successful refresh"""
        self.metrics.total_refreshes += 1
        self.metrics.successful_refreshes += 1
        self.metrics.consecutive_failures = 0
        self.metrics.last_refresh_time = datetime.now(timezone.utc)

        # Update average duration
        if self.metrics.average_refresh_duration_ms == 0:
            self.metrics.average_refresh_duration_ms = duration_ms
        else:
            self.metrics.average_refresh_duration_ms = (
                (self.metrics.average_refresh_duration_ms * (self.metrics.successful_refreshes - 1) + duration_ms) /
                self.metrics.successful_refreshes
            )

        # Update uptime percentage
        if self.metrics.total_refreshes > 0:
            self.metrics.uptime_percentage = (self.metrics.successful_refreshes / self.metrics.total_refreshes) * 100

    async def _update_metrics_failure(self, error_msg: str):
        """Update metrics after failed refresh"""
        self.metrics.total_refreshes += 1
        self.metrics.failed_refreshes += 1
        self.metrics.consecutive_failures += 1
        self.metrics.last_failure_time = datetime.now(timezone.utc)
        self.metrics.last_failure_reason = error_msg

        # Update uptime percentage
        if self.metrics.total_refreshes > 0:
            self.metrics.uptime_percentage = (self.metrics.successful_refreshes / self.metrics.total_refreshes) * 100

    async def _save_metrics(self):
        """Save metrics to file"""
        try:
            metrics_data = {
                "total_refreshes": self.metrics.total_refreshes,
                "successful_refreshes": self.metrics.successful_refreshes,
                "failed_refreshes": self.metrics.failed_refreshes,
                "consecutive_failures": self.metrics.consecutive_failures,
                "last_refresh_time": self.metrics.last_refresh_time.isoformat() if self.metrics.last_refresh_time else None,
                "last_failure_time": self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None,
                "last_failure_reason": self.metrics.last_failure_reason,
                "average_refresh_duration_ms": self.metrics.average_refresh_duration_ms,
                "uptime_percentage": self.metrics.uptime_percentage,
                "current_status": self.status.value,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

            async with aiofiles.open(self.metrics_file, 'w') as f:
                await f.write(json.dumps(metrics_data, indent=2))

        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    async def _load_metrics(self):
        """Load metrics from file"""
        try:
            if self.metrics_file.exists():
                async with aiofiles.open(self.metrics_file, 'r') as f:
                    data = json.loads(await f.read())

                self.metrics = TokenMetrics(
                    total_refreshes=data.get("total_refreshes", 0),
                    successful_refreshes=data.get("successful_refreshes", 0),
                    failed_refreshes=data.get("failed_refreshes", 0),
                    consecutive_failures=data.get("consecutive_failures", 0),
                    last_refresh_time=datetime.fromisoformat(data["last_refresh_time"]) if data.get("last_refresh_time") else None,
                    last_failure_time=datetime.fromisoformat(data["last_failure_time"]) if data.get("last_failure_time") else None,
                    last_failure_reason=data.get("last_failure_reason"),
                    average_refresh_duration_ms=data.get("average_refresh_duration_ms", 0.0),
                    uptime_percentage=data.get("uptime_percentage", 100.0)
                )

                logger.info(f"Metrics loaded: {self.metrics.successful_refreshes}/{self.metrics.total_refreshes} refreshes")

        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")

    async def _alert_manual_auth_needed(self, reason: str):
        """Send alert that manual authentication is needed"""
        alert_msg = f"CRITICAL: Manual Schwab authentication required!\nReason: {reason}"
        logger.critical(alert_msg)

        # Write to alert file
        alert_file = Path("backend/AUTH_ALERT.txt")
        with open(alert_file, 'w') as f:
            f.write(f"{datetime.now()}\n{alert_msg}\n")

        # Trigger callback
        if self.on_manual_auth_needed:
            await self.on_manual_auth_needed(reason)

        # Could add webhook/email alerts here
        if self.config.get("alert_webhook_url"):
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(self.config["alert_webhook_url"], json={"text": alert_msg})
            except:
                pass

    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive token status"""
        status = {
            "health": self.status.value,
            "has_token": self.token is not None,
            "metrics": asdict(self.metrics) if self.metrics else {},
            "config": {
                "refresh_before_expiry_hours": self.refresh_before_expiry_hours,
                "refresh_check_interval_minutes": self.refresh_check_interval_minutes,
                "max_retry_attempts": self.max_retry_attempts
            }
        }

        if self.token:
            now = datetime.now(timezone.utc)
            expires_at = self.token.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            time_until_expiry = expires_at - now
            hours_until_expiry = time_until_expiry.total_seconds() / 3600

            status["token"] = {
                "expires_at": expires_at.isoformat(),
                "hours_until_expiry": round(hours_until_expiry, 2),
                "refresh_count": self.token.refresh_count,
                "last_refresh": self.token.last_refresh.isoformat() if self.token.last_refresh else None,
                "next_refresh_scheduled": self.token.next_refresh_scheduled.isoformat() if self.token.next_refresh_scheduled else None
            }

        return status


# Singleton instance
_token_manager: Optional[TokenManager] = None

def get_token_manager() -> TokenManager:
    """Get singleton TokenManager instance"""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager