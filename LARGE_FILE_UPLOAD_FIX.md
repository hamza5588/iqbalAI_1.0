# Large File Upload Fix - Steps to Apply

## Problem
50MB file uploads are not reaching Flask - the request times out before reaching the server.

## Root Causes Identified
1. **Nginx client_body_timeout** was defaulting to 60 seconds (too short for large uploads)
2. **Browser fetch timeout** - no explicit timeout handling for large uploads
3. **Nginx config not reloaded** - changes won't take effect until nginx is restarted

## Changes Made

### 1. Nginx Configuration (`nginx.conf`)
✅ Added `client_body_timeout 1800s` (30 minutes) - CRITICAL for large uploads
✅ Added `send_timeout 1800s` 
✅ Added `client_body_in_file_only clean` to use temp files instead of memory
✅ These are set at both server level and location level

### 2. Frontend Upload (`templates/chat.html`)
✅ **Replaced fetch with XMLHttpRequest** - Better for large file uploads
✅ Added 30-minute timeout (1800000ms) for uploads
✅ Added upload progress tracking (shows percentage and speed)
✅ Added better error handling for timeout and network errors

## REQUIRED STEPS TO APPLY FIX

### Step 1: Reload Nginx (CRITICAL - Must do this first!)
```bash
# SSH into your server
cd ~/iqbalAI_1.0

# Reload nginx configuration
docker-compose exec nginx nginx -s reload

# OR restart nginx container
docker-compose restart nginx

# Verify nginx is running with new config
docker-compose exec nginx nginx -t
```

### Step 2: Verify Configuration
Check that nginx picked up the new settings:
```bash
docker-compose exec nginx cat /etc/nginx/nginx.conf | grep -A 5 "client_body_timeout"
```

You should see:
```
client_body_timeout 1800s;
```

### Step 3: Test Upload
1. Upload a 50MB file through the web interface
2. Check nginx logs for the request:
   ```bash
   docker-compose logs -f nginx | grep create_lesson
   ```
3. Check Flask logs:
   ```bash
   docker-compose logs -f flask_app1 | grep CREATE_LESSON
   ```

### Step 4: Monitor for Errors
Watch for these common issues:

**If still timing out:**
- Check browser console for errors
- Check nginx error logs: `docker-compose logs nginx | grep -i error`
- Verify file is actually being sent (check Network tab in browser dev tools)

**If getting 413 error:**
- This means `client_max_body_size` is being exceeded
- Check actual file size vs 100MB limit

**If request never appears in logs:**
- Browser may be timing out before request completes
- Check browser Network tab - look for cancelled requests
- Try using a smaller test file first (10MB) to verify setup

## Configuration Summary

### Nginx Settings (for `/api/lessons/create_lesson`)
- `client_max_body_size`: 100M
- `client_body_buffer_size`: 10M  
- `client_body_timeout`: 1800s (30 minutes) ⭐ **CRITICAL**
- `send_timeout`: 1800s (30 minutes)
- `proxy_read_timeout`: 1800s (30 minutes)
- `proxy_send_timeout`: 1800s (30 minutes)
- `proxy_connect_timeout`: 1800s (30 minutes)
- `proxy_buffering`: off
- `client_body_in_file_only`: clean

### Flask Settings
- `MAX_CONTENT_LENGTH`: 100MB (already configured in `app/__init__.py`)

### Frontend Settings
- **XMLHttpRequest** (replaced fetch for better large file handling)
- Upload timeout: 30 minutes (1800000ms)
- Upload progress tracking enabled

## Troubleshooting

### Request never reaches Flask
1. ✅ **Did you reload nginx?** (Most common issue!)
2. Check nginx access logs: `docker-compose logs nginx | tail -50`
3. Check nginx error logs: `docker-compose exec nginx tail -50 /var/log/nginx/error.log`
4. Verify browser is actually sending the request (Network tab in DevTools)

### Browser timeout
- The 30-minute timeout should handle most uploads
- For very slow connections, you may need to increase browser timeout further
- Check browser console for timeout errors

### Still having issues?
1. Test with a smaller file first (5-10MB) to verify the setup works
2. Check upload speed - if < 100KB/s, 50MB will take > 8 minutes
3. Verify there are no firewall or proxy timeouts between browser and server
4. Check if the file is actually 50MB (check file properties)

## Notes
- The `client_body_timeout` is the **most critical** setting - without it, nginx will close the connection after 60 seconds by default
- **XMLHttpRequest is used instead of fetch** for better reliability with large file uploads
- Large files are written to temp files (not memory) to prevent memory issues
- All timeouts are set to 30 minutes to handle even very slow connections
- Upload progress is shown in the browser console (percentage, speed, ETA)

## Why XMLHttpRequest instead of Fetch?
- Better timeout handling for large uploads
- Upload progress tracking (onprogress event)
- More reliable for large file transfers
- Better browser compatibility
- Can show real-time upload progress to users

