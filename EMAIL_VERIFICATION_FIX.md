# Email Verification Fix for Production Deployment

## Problem
Email verification links were failing on production server with "Invalid or expired verification link" error, even though it worked on localhost.

## Root Cause
The verification tokens were stored in an **in-memory dictionary** (`verification_tokens = {}`), which:
1. Gets cleared when the server restarts
2. Is not shared across multiple server workers/instances
3. Is not persistent across deployments

## Solution
Converted verification tokens to use **database storage** instead of in-memory dictionaries.

## Changes Made

### 1. Added Database Models (`app/models/database_models.py`)
- Added `EmailVerificationToken` model to store email verification tokens
- Added `PasswordResetToken` model to store password reset OTPs
- Both models include expiration tracking and usage status

### 2. Updated Auth Routes (`app/routes/auth.py`)
- Replaced in-memory `verification_tokens` dictionary with database queries
- Replaced in-memory `reset_tokens` dictionary with database queries
- Updated all token operations to use SQLAlchemy ORM
- Improved URL generation for production deployment

### 3. Added Server URL Configuration (`app/config.py`)
- Added `SERVER_URL` configuration option for production deployments
- Falls back to request headers (X-Forwarded-Host) if SERVER_URL not set
- Handles development vs production URL generation automatically

## Configuration for Production

### Set SERVER_URL Environment Variable

Add to your `.env` file or environment variables:

```env
SERVER_URL=https://iqbalai.com
```

Or if you're using HTTP:
```env
SERVER_URL=http://iqbalai.com
```

**Important**: Do NOT include a trailing slash.

### Example `.env` file:
```env
DATABASE_URL=postgresql://user:password@localhost/dbname
SERVER_URL=https://iqbalai.com
SECRET_KEY=your-secret-key-here
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

## How It Works Now

1. **Token Generation**: When a user requests email verification, a token is:
   - Generated using `secrets.token_urlsafe(32)`
   - Stored in the `email_verification_tokens` table
   - Expires after 24 hours

2. **URL Generation**: The verification link is generated based on:
   - `SERVER_URL` environment variable (if set) - for production
   - `X-Forwarded-Host` header (if present) - for reverse proxy setups
   - Request host (fallback) - for development

3. **Token Verification**: When user clicks the link:
   - Token is looked up in the database
   - Expiration is checked
   - If valid, user can complete registration
   - Token is marked as used after successful registration

## Benefits

1. ✅ **Persistent**: Tokens survive server restarts
2. ✅ **Scalable**: Works with multiple server workers/instances
3. ✅ **Reliable**: Database-backed storage ensures consistency
4. ✅ **Clean**: Automatic cleanup of expired tokens possible
5. ✅ **Production-Ready**: Handles production URL generation correctly

## Database Migration

The new tables will be created automatically on next application start via SQLAlchemy's `Base.metadata.create_all()`.

If you need to manually create the tables:
```python
from app.utils.db import init_db
from app import create_app

app = create_app()
with app.app_context():
    init_db(app)
```

## Testing

1. **Development**: Should work as before (uses request host)
2. **Production**: 
   - Set `SERVER_URL` environment variable
   - Restart the application
   - Test email verification - links should now work correctly

## Troubleshooting

### Still getting "Invalid or expired verification link"?

1. **Check SERVER_URL**: Make sure `SERVER_URL` is set correctly in production
   ```bash
   echo $SERVER_URL  # Should output: https://iqbalai.com
   ```

2. **Check Database**: Verify tokens are being stored
   ```sql
   SELECT * FROM email_verification_tokens ORDER BY created_at DESC LIMIT 5;
   ```

3. **Check Logs**: Look for URL generation in logs
   ```bash
   grep "Verification email sent" logs/app.log
   ```

4. **Check Expiration**: Tokens expire after 24 hours
   - If token is expired, user needs to request a new verification email

### URL Generation Issues

If verification links still have wrong domain:

1. **For nginx/reverse proxy**: Make sure `X-Forwarded-Host` and `X-Forwarded-Proto` headers are set
2. **For direct deployment**: Set `SERVER_URL` environment variable explicitly
3. **Check request headers**: Look at what headers Flask receives in production

## Additional Notes

- Old in-memory tokens will be lost on deployment - this is expected
- New tokens will be stored in the database
- Consider adding a periodic cleanup job to remove expired tokens (older than 24 hours + some buffer)

