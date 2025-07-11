# Schwab OAuth 2.0 Setup Guide

This guide walks you through setting up OAuth 2.0 authentication with Schwab for your trading copilot.

## Prerequisites

1. **Schwab Developer Account**: Register at [developer.schwab.com](https://developer.schwab.com)
2. **App Registration**: Create an app in the Schwab Developer Portal
3. **API Access**: Request access to the Trader API

## Step 1: Register Your App

1. Go to the [Schwab Developer Portal](https://developer.schwab.com)
2. Sign in with your Schwab credentials
3. Create a new app:
   - **App Name**: Your trading copilot name
   - **App Type**: Individual
   - **Callback URL**: `https://127.0.0.1` (for local development)
   - **API Product**: Trader API - Individual

4. After approval, note down:
   - **Client ID** (Consumer Key)
   - **Client Secret**

## Step 2: Set Environment Variables

Set these environment variables:

```bash
export SCHWAB_CLIENT_ID="your_client_id_here"
export SCHWAB_CLIENT_SECRET="your_client_secret_here"
export SCHWAB_REDIRECT_URI="https://127.0.0.1"  # Optional, defaults to this
```

Or create a `.env` file:
```
SCHWAB_CLIENT_ID=your_client_id_here
SCHWAB_CLIENT_SECRET=your_client_secret_here
SCHWAB_REDIRECT_URI=https://127.0.0.1
```

## Step 3: Run OAuth Setup

### Option A: Command Line Setup (Recommended)

```bash
cd whispr/backend
python setup_schwab_oauth.py
```

This will:
1. Open your browser to the Schwab authorization page
2. Prompt you to log in and grant permissions
3. Guide you through copying the authorization code
4. Exchange the code for access/refresh tokens
5. Save tokens to `~/.schwab_tokens.json`

### Option B: API Endpoints

1. **Check OAuth Status**:
   ```bash
   curl http://localhost:8000/oauth/status
   ```

2. **Get Authorization URL**:
   ```bash
   curl http://localhost:8000/oauth/authorize-url
   ```

3. **Visit the URL**, complete authorization, and copy the code from the redirect URL

4. **Exchange Code for Tokens**:
   ```bash
   curl -X POST http://localhost:8000/oauth/exchange-code \
        -H "Content-Type: application/json" \
        -d '{"code": "your_authorization_code_here"}'
   ```

## Step 4: Verify Setup

After successful authorization:

1. **Check Status**:
   ```bash
   curl http://localhost:8000/oauth/status
   ```

2. **Test Data Provider**:
   ```bash
   curl http://localhost:8000/data-provider/status
   ```

3. **Get Market Quote**:
   ```bash
   curl http://localhost:8000/data-provider/quote/SPY
   ```

## Token Management

### Automatic Refresh
- Access tokens expire in **30 minutes**
- Refresh tokens expire in **7 days**
- Tokens are automatically refreshed when needed
- No manual intervention required during normal operation

### Manual Refresh
```bash
curl -X POST http://localhost:8000/oauth/refresh
```

### Re-authorization
If refresh tokens expire (after 7 days), re-run the setup:
```bash
python setup_schwab_oauth.py
```

## File Structure

```
~/.schwab_tokens.json       # Stored tokens (automatically managed)
whispr/backend/
├── schwab_config.py        # OAuth implementation
├── setup_schwab_oauth.py   # Setup script
└── main.py                 # API with OAuth endpoints
```

## OAuth Flow Details

This implementation follows the [Schwab OAuth 2.0 specification](https://developer.schwab.com):

1. **Authorization Request**: User visits authorization URL
2. **User Consent**: User logs in and grants permissions
3. **Authorization Code**: Schwab redirects with authorization code
4. **Token Exchange**: Code is exchanged for access/refresh tokens
5. **API Access**: Access token is used for API calls
6. **Token Refresh**: Refresh token renews access tokens

## Security Notes

- **Client Secret**: Never expose in client-side code
- **Tokens**: Stored locally in `~/.schwab_tokens.json`
- **HTTPS Required**: All OAuth endpoints require HTTPS
- **Token Rotation**: Tokens are automatically rotated

## Troubleshooting

### Common Issues

1. **"No OAuth configuration found"**
   - Check environment variables are set
   - Verify Client ID and Client Secret

2. **"Token exchange failed"**
   - Ensure authorization code is complete
   - Check redirect URI matches app registration
   - Verify Client ID/Secret are correct

3. **"Failed to refresh token"**
   - Refresh token may be expired (7 days)
   - Re-run authorization flow

4. **"Data provider not initialized"**
   - Complete OAuth setup first
   - Check token validity with `/oauth/status`

### Debug Steps

1. Check OAuth status:
   ```bash
   curl http://localhost:8000/oauth/status
   ```

2. Verify environment variables:
   ```bash
   echo $SCHWAB_CLIENT_ID
   echo $SCHWAB_CLIENT_SECRET
   ```

3. Check token file:
   ```bash
   cat ~/.schwab_tokens.json
   ```

4. Re-run setup with fresh authorization:
   ```bash
   python setup_schwab_oauth.py
   ```

## Production Deployment

For production:

1. Use secure environment variable management
2. Set proper redirect URIs in Schwab app registration
3. Implement proper error handling for token expiration
4. Consider implementing token refresh scheduling
5. Use HTTPS for all endpoints

## API Reference

### OAuth Endpoints

- `GET /oauth/status` - Check authorization status
- `GET /oauth/authorize-url` - Get authorization URL
- `POST /oauth/exchange-code` - Exchange authorization code
- `POST /oauth/refresh` - Refresh access tokens

### Data Provider Endpoints

- `GET /data-provider/status` - Provider status
- `GET /data-provider/quote/{symbol}` - Get quote
- `POST /data-provider/connect` - Connect to streamer
- `POST /data-provider/subscribe` - Subscribe to symbols

---

For additional help, consult:
- [Schwab Developer Documentation](https://developer.schwab.com)
- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)
- Your app registration in the Schwab Developer Portal 