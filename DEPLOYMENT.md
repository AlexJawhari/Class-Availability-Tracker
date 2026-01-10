# Deployment Guide

This guide covers deploying the UTD Coursebook Tracker to various hosting platforms.

## Platform Comparison

### Railway (Recommended)

**Pros:**
- Free tier: $5 credit/month (usually sufficient)
- Easy setup with GitHub integration
- Good for Discord bots (persistent connections)
- Auto-detects Dockerfile
- No sleep/spin-down issues with Uptime Robot

**Cons:**
- Free tier has usage limits (monitor usage)
- May require credit card (no charges on free tier)

**Setup:**
1. Go to [railway.app](https://railway.app) and sign up
2. Click "New Project" → "Deploy from GitHub repo"
3. Select this repository
4. Add environment variables (see Environment Variables section)
5. Deploy automatically starts
6. Copy service URL for Uptime Robot

### Render (Alternative)

**Pros:**
- Free tier available (no credit card initially)
- Easy GitHub integration
- Good documentation

**Cons:**
- Free tier services spin down after 15 minutes of inactivity
- Requires Uptime Robot to keep alive
- Slower cold starts after spin-down

**Setup:**
1. Go to [render.com](https://render.com) and sign up
2. Click "New" → "Web Service"
3. Connect GitHub repository
4. Configure:
   - **Name**: utd-coursebook-tracker (or your choice)
   - **Environment**: Docker
   - **Build Command**: (leave empty - Dockerfile handles it)
   - **Start Command**: `python -u -m src.bot`
   - **Health Check Path**: `/healthz` or `/`
5. Add environment variables (see Environment Variables section)
6. Deploy
7. Set up Uptime Robot (see below)

## Environment Variables

Set these in your hosting platform's environment variables section:

### Required Variables

```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key_here
```

**Important Notes:**
- `DISCORD_BOT_TOKEN`: Get from [Discord Developer Portal](https://discord.com/developers/applications)
- `SUPABASE_URL`: Get from Supabase Dashboard → Settings → API → Project URL
- `SUPABASE_KEY`: **MUST be the SERVICE ROLE KEY** (not anon key). Get from Supabase Dashboard → Settings → API → service_role key

### Optional Variables

```env
PORT=8080                    # Usually auto-set by platform
LOG_ACCESS_KEY=debugme       # For protected endpoints (/logs, /test-scrape)
BROWSERLESS_TOKEN=...        # Only if using Browserless.io cloud browser
```

## Uptime Robot Setup (Free Tier Required)

Both Render free tier and Railway benefit from Uptime Robot to ensure the service stays alive and healthy.

1. **Sign up**: Go to [uptimerobot.com](https://uptimerobot.com) (free tier: 50 monitors)

2. **Add Monitor**:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: UTD Coursebook Tracker
   - **URL**: 
     - Railway: `https://your-app.railway.app/healthz`
     - Render: `https://your-app.onrender.com/healthz`
   - **Monitoring Interval**: 5 minutes (recommended)
   - **Alert Contacts**: Add your email/notification preferences

3. **Save**: Monitor will ping your service every 5 minutes

**Why This Works:**
- Keeps Render services from spinning down
- Provides health monitoring
- Sends alerts if service goes down
- Free tier is sufficient for one service

## Verification Steps

After deployment:

1. **Check Health**:
   ```bash
   curl https://your-app.railway.app/healthz
   # Should return: "Bot is alive! Scraper orchestrator ready."
   ```

2. **Check Status**:
   ```bash
   curl https://your-app.railway.app/status
   # Should return JSON with bot status, database connection, etc.
   ```

3. **Check Logs** (if `LOG_ACCESS_KEY` is set):
   ```bash
   curl "https://your-app.railway.app/logs?key=YOUR_LOG_ACCESS_KEY"
   ```

4. **Test Scraping** (if `LOG_ACCESS_KEY` is set):
   ```bash
   curl "https://your-app.railway.app/test-scrape?query=CS 4349&key=YOUR_LOG_ACCESS_KEY"
   ```

5. **Test Discord Bot**:
   - Invite bot to your server
   - Run `/track CS 4349 001` (or any course)
   - Check `/status` endpoint - should show subscription count increased

## Troubleshooting Deployment

### Build Fails

**Issue**: Docker build fails, especially with `curl_cffi`.

**Solutions**:
- This is okay! The app works without `curl_cffi`
- Check logs to confirm token extraction scraper is available
- If build fails completely, check Dockerfile logs for specific errors
- Try removing `curl_cffi` from requirements.txt if build consistently fails

### Service Won't Start

**Issue**: Service deploys but crashes immediately.

**Solutions**:
- Check environment variables are set correctly
- Verify `DISCORD_BOT_TOKEN` is valid
- Verify `SUPABASE_KEY` is the service role key (not anon key)
- Check logs for specific error messages

### Health Check Fails

**Issue**: Platform reports health check failed.

**Solutions**:
- Verify `/healthz` endpoint returns 200
- Check `PORT` environment variable matches platform's expected port
- Railway/Render usually auto-set `PORT`, but verify it's being used
- Check logs for binding errors

### Bot Doesn't Respond

**Issue**: Discord commands don't work.

**Solutions**:
- Verify bot is online in Discord (should appear as online in member list)
- Check `/status` endpoint - `bot_status` should be "online"
- Verify `DISCORD_BOT_TOKEN` is correct
- Check Discord bot permissions in your server
- Ensure bot is in the server where you're testing commands

### Scraping Fails

**Issue**: Scraping returns empty results or gets CAPTCHA'd.

**Solutions**:
- Check `/test-scrape` endpoint to see which method is being used
- Token extraction method should bypass most detection
- If all methods fail, check UTD Coursebook for API changes
- Check logs for specific error messages
- Verify network connectivity from hosting platform

## Monitoring & Maintenance

### Regular Checks

1. **Weekly**: Check `/status` endpoint to verify service health
2. **Monthly**: Review usage on Railway/Render dashboard
3. **Semester Changes**: Update `CURRENT_TERM` in `src/checker_http.py` if UTD term format changes

### Term Updates

UTD Coursebook uses term codes like:
- Spring 2026 = `term_26s`
- Fall 2025 = `term_25f`
- Summer 2025 = `term_25u`

Update `CURRENT_TERM` in `src/checker_http.py` when semesters change.

### Resource Monitoring

- **Railway**: Monitor usage in dashboard (free tier: $5/month)
- **Render**: Monitor in dashboard (free tier: 750 hours/month)
- **Discord**: Bot has rate limits but should be fine for normal use

## Migration Between Platforms

If you need to migrate from Render to Railway (or vice versa):

1. Export environment variables from old platform
2. Set up new platform following setup instructions
3. Add all environment variables
4. Update Uptime Robot URL to new service URL
5. Test thoroughly before shutting down old service
6. Keep old service running for a few days as backup

## Cost Management

### Free Tier Limitations

- **Railway**: $5 credit/month - monitor usage dashboard
- **Render**: 750 hours/month - services may spin down without Uptime Robot
- **Uptime Robot**: 50 monitors - sufficient for this project
- **Supabase**: Free tier usually sufficient for small-scale use

### Scaling Considerations

If you need to scale:
- Upgrade Railway plan ($5/month → $10/month for more resources)
- Use Render paid tier ($7/month) for no spin-downs
- Monitor Supabase usage and upgrade if needed
- Consider rate limiting if many users use the bot

## Security Best Practices

1. **Never commit** `.env` file or environment variables
2. **Use service role key** (not anon key) for Supabase
3. **Protect debug endpoints** with `LOG_ACCESS_KEY`
4. **Rotate tokens** periodically if exposed
5. **Monitor logs** for suspicious activity
6. **Keep dependencies** updated for security patches