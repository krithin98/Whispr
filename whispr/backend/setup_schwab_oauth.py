#!/usr/bin/env python3
"""
Schwab OAuth 2.0 Setup Script

This script helps you set up OAuth 2.0 authentication with Schwab.
Run this script to authorize your application and get access tokens.

Prerequisites:
1. Register your app at developer.schwab.com
2. Get your Client ID and Client Secret
3. Set environment variables or enter them when prompted

Environment Variables:
- SCHWAB_CLIENT_ID: Your app's Client ID
- SCHWAB_CLIENT_SECRET: Your app's Client Secret  
- SCHWAB_REDIRECT_URI: Your callback URL (default: https://127.0.0.1)
"""

import asyncio
import os
import webbrowser
import urllib.parse
import requests
import json
import base64
from datetime import datetime, timedelta
from schwab_config import SchwabOAuthManager, initialize_schwab_oauth

def get_credentials():
    """Get Schwab credentials from environment or user input"""
    client_id = os.getenv("SCHWAB_CLIENT_ID")
    client_secret = os.getenv("SCHWAB_CLIENT_SECRET")
    redirect_uri = os.getenv("SCHWAB_REDIRECT_URI", "https://127.0.0.1")
    
    if not client_id:
        print("🔐 Schwab Client ID not found in environment")
        client_id = input("Enter your Schwab Client ID: ").strip()
    
    if not client_secret:
        print("🔐 Schwab Client Secret not found in environment")
        client_secret = input("Enter your Schwab Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("❌ Client ID and Client Secret are required")
        return None, None, None
    
    return client_id, client_secret, redirect_uri

def extract_auth_code_from_url(full_url):
    """Extract and decode the authorization code from the full redirect URL"""
    
    print(f"📋 Processing URL...")
    
    # Parse the URL
    parsed = urllib.parse.urlparse(full_url)
    query_params = urllib.parse.parse_qs(parsed.query)
    
    print(f"🔍 Found query parameters: {list(query_params.keys())}")
    
    if 'code' in query_params:
        # Get the code (parse_qs returns lists)
        auth_code = query_params['code'][0]
        
        print(f"✅ Raw authorization code found")
        
        # URL decode if needed
        decoded_code = urllib.parse.unquote(auth_code)
        
        if decoded_code != auth_code:
            print(f"🔄 URL decoded successfully")
        
        return decoded_code
    else:
        print("❌ No 'code' parameter found in URL")
        return None

def exchange_code_for_tokens_fixed(auth_code, client_id, client_secret, redirect_uri):
    """Exchange authorization code for access tokens with SSL fix for macOS"""
    
    # Prepare credentials
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    # Prepare request
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri
    }
    
    try:
        # Disable SSL warnings for macOS
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Make request with SSL verification disabled (for macOS issues)
        response = requests.post(
            "https://api.schwabapi.com/v1/oauth/token",
            headers=headers,
            data=data,
            verify=False  # Disable SSL verification for macOS
        )
        
        if response.status_code == 200:
            tokens = response.json()
            
            # Calculate expiration time
            expires_in = tokens.get("expires_in", 1800)  # 30 minutes default
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            # Add expiration time to tokens
            tokens["expires_at"] = expires_at.isoformat()
            
            # Save tokens
            token_file = os.path.expanduser("~/.schwab_tokens.json")
            with open(token_file, "w") as f:
                json.dump(tokens, f, indent=2)
            
            print("✅ Tokens saved successfully!")
            print(f"📁 Location: {token_file}")
            print(f"🕐 Access token expires: {expires_at}")
            
            return tokens
        else:
            print(f"❌ Token exchange failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error during token exchange: {e}")
        return None

async def setup_oauth():
    """Main setup function"""
    print("🚀 Schwab OAuth 2.0 Setup")
    print("=" * 50)
    
    # Get credentials
    client_id, client_secret, redirect_uri = get_credentials()
    if not client_id or not client_secret:
        return
    
    # Create OAuth manager
    oauth_manager = SchwabOAuthManager(client_id, client_secret, redirect_uri)
    
    # Check if already authorized
    await oauth_manager.load_tokens()
    if oauth_manager.is_authorized():
        print("✅ Already authorized!")
        try:
            token = await oauth_manager.get_valid_access_token()
            print(f"✅ Valid access token: {token[:20]}...")
            print(f"✅ Token expires: {oauth_manager.tokens.expires_at}")
            return
        except Exception as e:
            print(f"⚠️ Existing token invalid: {e}")
            print("Will re-authorize...")
    
    # Start OAuth flow
    print("\n🔗 Starting OAuth 2.0 Authorization Flow")
    print("-" * 40)
    
    # Step 1: Get authorization URL
    auth_url = oauth_manager.get_authorization_url()
    print("1. Opening authorization URL in your browser...")
    print(f"   URL: {auth_url}")
    
    # Try to open browser automatically
    try:
        webbrowser.open(auth_url)
        print("   ✅ Browser opened automatically")
    except:
        print("   ⚠️ Could not open browser automatically")
        print("   Please copy and paste the URL above into your browser")
    
    print("\n2. Complete the authorization in your browser:")
    print("   - Log in to Schwab")
    print("   - Grant permissions to your app")
    print("   - You'll be redirected to a 404 page (this is expected)")
    
    print("\n3. Copy the ENTIRE URL from the address bar:")
    print("   The page will show a 404 error, but the URL contains the code")
    print("   Copy the complete URL and paste it below")
    
    # Get full redirect URL from user
    full_url = input("\nPaste the full redirect URL here: ").strip()
    
    if not full_url:
        print("❌ No URL provided")
        return
    
    # Extract authorization code from URL
    auth_code = extract_auth_code_from_url(full_url)
    
    if not auth_code:
        print("❌ Could not extract authorization code from URL")
        return
    
    # Step 2: Exchange code for tokens
    print("\n🔄 Exchanging authorization code for tokens...")
    try:
        # First try the standard method
        tokens = await oauth_manager.exchange_code_for_tokens(auth_code)
        print("✅ Authorization successful!")
        print(f"   Access Token: {tokens.access_token[:20]}...")
        print(f"   Refresh Token: {tokens.refresh_token[:20]}...")
        print(f"   Expires At: {tokens.expires_at}")
        print(f"   Token Type: {tokens.token_type}")
        print(f"   Scope: {tokens.scope}")
        
        # Test the token
        print("\n🧪 Testing access token...")
        test_token = await oauth_manager.get_valid_access_token()
        print(f"✅ Token test successful: {test_token[:20]}...")
        
        print("\n🎉 OAuth setup complete!")
        print("Your tokens have been saved and your app is ready to use Schwab API.")
        
    except Exception as e:
        print(f"⚠️  Standard method failed: {e}")
        print("🔄 Trying SSL-fixed method for macOS...")
        
        # Fallback to our SSL-fixed method
        token_dict = exchange_code_for_tokens_fixed(auth_code, client_id, client_secret, redirect_uri)
        
        if token_dict:
            print("\n🎉 SUCCESS! Schwab authentication complete!")
            print("Your tokens have been saved and your app is ready to use Schwab API.")
        else:
            print("\n❌ All methods failed. Please try again with a fresh authorization code.")
            print("\nTroubleshooting:")
            print("- Make sure you copied the complete redirect URL")
            print("- Check that your Client ID and Client Secret are correct")
            print("- Verify your redirect URI matches what's registered in Schwab")

def print_env_setup():
    """Print environment variable setup instructions"""
    print("\n📝 Environment Variable Setup")
    print("=" * 40)
    print("For easier setup, you can set these environment variables:")
    print()
    print("export SCHWAB_CLIENT_ID='your_client_id_here'")
    print("export SCHWAB_CLIENT_SECRET='your_client_secret_here'")
    print("export SCHWAB_REDIRECT_URI='https://127.0.0.1'  # Optional")
    print()
    print("Or create a .env file in your project root:")
    print("SCHWAB_CLIENT_ID=your_client_id_here")
    print("SCHWAB_CLIENT_SECRET=your_client_secret_here")
    print("SCHWAB_REDIRECT_URI=https://127.0.0.1")

def print_next_steps():
    """Print next steps after setup"""
    print("\n📋 Next Steps")
    print("=" * 20)
    print("1. Your OAuth tokens are saved in ~/.schwab_tokens.json")
    print("2. Tokens will automatically refresh when needed")
    print("3. Access tokens expire in 30 minutes")
    print("4. Refresh tokens expire in 7 days")
    print("5. Run this script again if you need to re-authorize")
    print()
    print("You can now:")
    print("- Use the Schwab API for trading")
    print("- Get real-time market data")
    print("- Access account information")

async def main():
    """Main function"""
    try:
        await setup_oauth()
        print_next_steps()
    except KeyboardInterrupt:
        print("\n\n⏹️ Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("\nFor help, check:")
        print("- Schwab Developer Portal: https://developer.schwab.com")
        print("- Your app registration details")
        print("- Network connectivity")
    
    print_env_setup()

if __name__ == "__main__":
    asyncio.run(main()) 
