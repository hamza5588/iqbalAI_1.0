# Nginx Diagnostic Steps - Large File Upload Issue

## The Problem
- ✅ Works perfectly when running Flask directly (`python run.py`) - no nginx
- ❌ Doesn't work with nginx/Docker
- Request gets stuck at "pending" with 0 bytes transferred

This confirms: **The issue is nginx, NOT Flask or the browser**

## Critical Steps to Fix

### Step 1: Verify Nginx Config is Loaded

SSH into your server and run:

```bash
cd ~/iqbalAI_1.0

# Check if nginx config file is being read
docker-compose exec nginx cat /etc/nginx/nginx.conf | grep -A 10 "create_lesson"
```

You should see the location block with timeouts. If not, the config file isn't being mounted properly.

### Step 2: Reload Nginx (REQUIRED!)

```bash
# Method 1: Reload config (preferred - doesn't drop connections)
docker-compose exec nginx nginx -s reload

# Method 2: Restart nginx container (if reload doesn't work)
docker-compose restart nginx

# Verify nginx is running
docker-compose ps nginx
```

### Step 3: Test Nginx Config Syntax

```bash
# Check for syntax errors
docker-compose exec nginx nginx -t
```

If there are errors, fix them before proceeding.

### Step 4: Verify Config Values Are Applied

```bash
# Check client_body_timeout is set
docker-compose exec nginx cat /etc/nginx/nginx.conf | grep client_body_timeout

# Should show:
# client_body_timeout 1800s;  (at server level)
# client_body_timeout 1800s;  (at location level for create_lesson)
```

### Step 5: Check Nginx Error Logs

```bash
# Watch nginx error logs in real-time
docker-compose logs -f nginx 2>&1 | grep -i error

# Or check error log file
docker-compose exec nginx tail -50 /var/log/nginx/error.log
```

Look for:
- `413 Request Entity Too Large` - means file size limit exceeded
- `408 Request Timeout` - means timeout too short
- `upstream timed out` - means proxy timeout
- `client request body is buffering to a temporary file` - normal for large files

### Step 6: Monitor Access Logs During Upload

In one terminal:
```bash
docker-compose logs -f nginx | grep create_lesson
```

In another terminal, try uploading your file. You should see the POST request appear.

### Step 7: Check Request Reaches Flask

```bash
docker-compose logs -f flask_app1 | grep CREATE_LESSON
```

If you see "CREATE_LESSON REQUEST RECEIVED", the request reached Flask. If not, nginx is blocking it.

## Common Issues & Solutions

### Issue 1: Config Not Applied
**Symptom**: Changes in nginx.conf don't take effect
**Solution**: 
- Make sure you reload nginx: `docker-compose exec nginx nginx -s reload`
- Verify config file is mounted: `docker-compose exec nginx ls -la /etc/nginx/nginx.conf`

### Issue 2: Location Block Not Matching
**Symptom**: Request goes to wrong location block (gets 300s timeout instead of 1800s)
**Solution**: The regex location should work, but verify:
```bash
docker-compose exec nginx nginx -T | grep -A 20 "create_lesson"
```

### Issue 3: Rate Limiting Blocking
**Symptom**: Request gets 429 or is dropped silently
**Solution**: The `limit_req zone=one burst=20 nodelay;` at line 84 applies to all requests. For large uploads, we might need to exclude the upload endpoint from rate limiting.

### Issue 4: Request Body Too Large for Buffer
**Symptom**: 413 error or request fails
**Solution**: Verify these are set:
- `client_max_body_size 100M;` ✅
- `client_body_buffer_size 10M;` ✅
- `client_body_in_file_only clean;` ✅ (uses temp file instead of memory)

## Test Upload Without Nginx (Verify Flask Works)

To confirm Flask can handle the file without nginx:

```bash
# Stop nginx
docker-compose stop nginx

# Access Flask directly (if port is exposed)
# Or temporarily expose Flask port in docker-compose.yml
# Then access at: http://your-server-ip:5000/api/lessons/create_lesson

# After testing, restart nginx
docker-compose start nginx
```

## Quick Fix: Increase Rate Limit Burst for Uploads

If rate limiting is the issue, we can increase the burst for large uploads. But first, let's verify if that's the problem by checking logs during an upload attempt.

## Debug Checklist

- [ ] Nginx config file exists and is readable
- [ ] Config file is mounted in docker-compose.yml
- [ ] Nginx was reloaded after config changes
- [ ] Nginx config syntax is valid (`nginx -t`)
- [ ] `client_body_timeout 1800s` appears in config
- [ ] Location block for create_lesson exists and has correct timeouts
- [ ] No errors in nginx error logs
- [ ] Request appears in nginx access logs
- [ ] Request reaches Flask (appears in Flask logs)

## Next Steps

1. **FIRST**: Reload nginx (`docker-compose exec nginx nginx -s reload`)
2. **THEN**: Try uploading the file again
3. **WATCH**: Monitor logs in real-time to see where it fails
4. **REPORT**: Share the logs if it still doesn't work

