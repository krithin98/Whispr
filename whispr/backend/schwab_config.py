"""
Schwab Streamer API Configuration and Helper Functions
"""

import os
import base64
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class SchwabTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime
    token_type: str = "Bearer"
    scope: str = "api"

@dataclass
class SchwabConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    schwab_client_customer_id: Optional[str] = None
    schwab_client_channel: str = "N9"
    schwab_client_function_id: str = "APIAPP"

class SchwabOAuthManager:
    """Manages Schwab OAuth 2.0 authentication flow"""
    
    BASE_URL = "https://api.schwabapi.com"
    AUTH_URL = f"{BASE_URL}/v1/oauth/authorize"
    TOKEN_URL = f"{BASE_URL}/v1/oauth/token"
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.tokens: Optional[SchwabTokens] = None
        self.token_file = os.path.expanduser("~/.schwab_tokens.json")
        
    def get_authorization_url(self) -> str:
        """Generate the authorization URL for step 1 of OAuth flow"""
        return f"{self.AUTH_URL}?client_id={self.client_id}&redirect_uri={self.redirect_uri}"
    
    def _get_auth_header(self) -> str:
        """Create the Basic Auth header for token requests"""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    async def exchange_code_for_tokens(self, authorization_code: str) -> SchwabTokens:
        """Exchange authorization code for access/refresh tokens (Step 2)"""
        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # URL decode the authorization code
        import urllib.parse
        decoded_code = urllib.parse.unquote(authorization_code)
        
        data = {
            "grant_type": "authorization_code",
            "code": decoded_code,
            "redirect_uri": self.redirect_uri
        }
        
        # Create SSL context that bypasses certificate verification (for macOS)
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(self.TOKEN_URL, headers=headers, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    
                    # Create tokens object
                    expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
                    self.tokens = SchwabTokens(
                        access_token=token_data["access_token"],
                        refresh_token=token_data["refresh_token"],
                        expires_at=expires_at,
                        token_type=token_data["token_type"],
                        scope=token_data["scope"]
                    )
                    
                    # Save tokens to file
                    await self.save_tokens()
                    
                    return self.tokens
                else:
                    error_text = await response.text()
                    raise Exception(f"Token exchange failed: {response.status} - {error_text}")
    
    async def refresh_access_token(self) -> SchwabTokens:
        """Refresh access token using refresh token (Step 4)"""
        if not self.tokens or not self.tokens.refresh_token:
            raise Exception("No refresh token available")
        
        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.tokens.refresh_token
        }
        
        # Create SSL context that bypasses certificate verification (for macOS)
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(self.TOKEN_URL, headers=headers, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    
                    # Update tokens
                    expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
                    self.tokens = SchwabTokens(
                        access_token=token_data["access_token"],
                        refresh_token=token_data["refresh_token"],
                        expires_at=expires_at,
                        token_type=token_data["token_type"],
                        scope=token_data["scope"]
                    )
                    
                    # Save updated tokens
                    await self.save_tokens()
                    
                    return self.tokens
                else:
                    error_text = await response.text()
                    raise Exception(f"Token refresh failed: {response.status} - {error_text}")
    
    async def get_valid_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary"""
        if not self.tokens:
            # Try to load from file
            await self.load_tokens()
        
        if not self.tokens:
            raise Exception("No tokens available. Please complete OAuth authorization flow.")
        
        # Check if token is expired or expires within 5 minutes
        if datetime.now() >= (self.tokens.expires_at - timedelta(minutes=5)):
            print("🔄 Access token expired or expiring soon, refreshing...")
            try:
                await self.refresh_access_token()
            except Exception as e:
                raise Exception(f"Failed to refresh token: {e}. Please re-authorize the application.")
        
        return self.tokens.access_token
    
    async def save_tokens(self):
        """Save tokens to local file"""
        if self.tokens:
            token_data = {
                "access_token": self.tokens.access_token,
                "refresh_token": self.tokens.refresh_token,
                "expires_at": self.tokens.expires_at.isoformat(),
                "token_type": self.tokens.token_type,
                "scope": self.tokens.scope
            }
            
            try:
                with open(self.token_file, 'w') as f:
                    json.dump(token_data, f, indent=2)
                print(f"✅ Tokens saved to {self.token_file}")
            except Exception as e:
                print(f"❌ Failed to save tokens: {e}")
    
    async def load_tokens(self):
        """Load tokens from local file"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                
                self.tokens = SchwabTokens(
                    access_token=token_data["access_token"],
                    refresh_token=token_data["refresh_token"],
                    expires_at=datetime.fromisoformat(token_data["expires_at"]),
                    token_type=token_data["token_type"],
                    scope=token_data["scope"]
                )
                print(f"✅ Tokens loaded from {self.token_file}")
            else:
                print(f"ℹ️ No token file found at {self.token_file}")
        except Exception as e:
            print(f"❌ Failed to load tokens: {e}")
    
    def is_authorized(self) -> bool:
        """Check if we have valid tokens"""
        return (self.tokens is not None and 
                self.tokens.access_token is not None and
                datetime.now() < self.tokens.expires_at)

class SchwabOrderManager:
    """Handles Schwab order placement and management"""
    
    def __init__(self, oauth_manager: SchwabOAuthManager):
        self.oauth_manager = oauth_manager
        self.base_url = "https://api.schwabapi.com"
    
    async def _make_api_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make authenticated API request"""
        access_token = await self.oauth_manager.get_valid_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            if method.upper() == "GET":
                async with session.get(url, headers=headers) as response:
                    return await self._handle_response(response)
            elif method.upper() == "POST":
                async with session.post(url, headers=headers, json=data) as response:
                    return await self._handle_response(response)
            elif method.upper() == "PUT":
                async with session.put(url, headers=headers, json=data) as response:
                    return await self._handle_response(response)
            elif method.upper() == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    return await self._handle_response(response)
    
    async def _handle_response(self, response):
        """Handle API response"""
        if response.status in [200, 201]:
            if response.content_type == 'application/json':
                return await response.json()
            else:
                return {"status": "success", "text": await response.text()}
        else:
            error_text = await response.text()
            raise Exception(f"API request failed: {response.status} - {error_text}")
    
    async def place_equity_order(self, account_hash: str, symbol: str, instruction: str, 
                               quantity: int, order_type: str = "MARKET", 
                               price: float = None, duration: str = "DAY") -> dict:
        """Place an equity order"""
        order_data = {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": duration,
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": instruction,
                    "quantity": quantity,
                    "instrument": {
                        "symbol": symbol,
                        "assetType": "EQUITY"
                    }
                }
            ]
        }
        
        if order_type == "LIMIT" and price:
            order_data["price"] = str(price)
        
        endpoint = f"/trader/v1/accounts/{account_hash}/orders"
        return await self._make_api_request("POST", endpoint, order_data)
    
    async def get_account_info(self, account_hash: str) -> dict:
        """Get account information"""
        endpoint = f"/trader/v1/accounts/{account_hash}"
        return await self._make_api_request("GET", endpoint)
    
    async def get_positions(self, account_hash: str) -> dict:
        """Get account positions"""
        endpoint = f"/trader/v1/accounts/{account_hash}/positions"
        return await self._make_api_request("GET", endpoint)
    
    async def get_orders(self, account_hash: str) -> dict:
        """Get orders for account"""
        endpoint = f"/trader/v1/accounts/{account_hash}/orders"
        return await self._make_api_request("GET", endpoint)

def get_schwab_config() -> Optional[SchwabConfig]:
    """Get Schwab configuration from environment variables"""
    client_id = os.getenv("SCHWAB_CLIENT_ID")
    client_secret = os.getenv("SCHWAB_CLIENT_SECRET")
    redirect_uri = os.getenv("SCHWAB_REDIRECT_URI", "https://127.0.0.1")
    
    if not client_id or not client_secret:
        return None
    
    # Try to load existing tokens
    oauth_manager = SchwabOAuthManager(client_id, client_secret, redirect_uri)
    
    config = SchwabConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        schwab_client_customer_id=os.getenv("SCHWAB_CLIENT_CUSTOMER_ID"),
        schwab_client_channel=os.getenv("SCHWAB_CLIENT_CHANNEL", "N9"),
        schwab_client_function_id=os.getenv("SCHWAB_CLIENT_FUNCTION_ID", "APIAPP")
    )
    
    return config

async def initialize_schwab_oauth() -> Optional[SchwabOAuthManager]:
    """Initialize Schwab OAuth manager"""
    config = get_schwab_config()
    if not config:
        return None
    
    oauth_manager = SchwabOAuthManager(
        config.client_id,
        config.client_secret,
        config.redirect_uri
    )
    
    # Try to load existing tokens
    await oauth_manager.load_tokens()
    
    return oauth_manager

# Example usage and testing
if __name__ == "__main__":
    async def test_oauth_flow():
        """Test the OAuth flow"""
        oauth_manager = await initialize_schwab_oauth()
        
        if not oauth_manager:
            print("❌ No Schwab configuration found")
            print("Set environment variables:")
            print("  - SCHWAB_CLIENT_ID")
            print("  - SCHWAB_CLIENT_SECRET")
            print("  - SCHWAB_REDIRECT_URI (optional, defaults to https://127.0.0.1)")
            return
        
        if not oauth_manager.is_authorized():
            print("🔐 Authorization required")
            print("1. Visit this URL to authorize the app:")
            print(f"   {oauth_manager.get_authorization_url()}")
            print("\n2. After authorizing, you'll be redirected to a 404 page.")
            print("3. Copy the 'code' parameter from the URL and paste it here:")
            
            auth_code = input("Authorization code: ").strip()
            
            try:
                tokens = await oauth_manager.exchange_code_for_tokens(auth_code)
                print(f"✅ Authorization successful!")
                print(f"   Access token expires at: {tokens.expires_at}")
            except Exception as e:
                print(f"❌ Authorization failed: {e}")
                return
        else:
            print("✅ Already authorized")
        
        # Test getting a valid token
        try:
            token = await oauth_manager.get_valid_access_token()
            print(f"✅ Valid access token obtained: {token[:20]}...")
        except Exception as e:
            print(f"❌ Failed to get valid token: {e}")
    
    asyncio.run(test_oauth_flow()) 