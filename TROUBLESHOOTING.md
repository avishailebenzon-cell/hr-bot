# HR Bot - Troubleshooting Guide

## Bot Commands Not Working

### Problem: Bot doesn't respond to `/start` or other commands

**Check these:**

1. Verify TELEGRAM_TOKEN is correct
   ```bash
   echo $TELEGRAM_TOKEN
   # Should not be empty
   ```

2. Check bot is running
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status": "ok", ...}
   ```

3. Verify in Telegram that you've found the right bot
   - Start your bot from the bot link BotFather gave you
   - Not from searching by name

4. Check logs for errors
   ```bash
   docker-compose logs -f hr_bot
   # Look for: ERROR, exception, traceback
   ```

---

## OAuth / Outlook Connection Fails

### Problem: "Connect Outlook" button doesn't work

**Check these:**

1. Verify Azure App Registration exists
   - Go to [Azure Portal](https://portal.azure.com)
   - App Registrations → find your app

2. Verify credentials in `.env`
   ```bash
   echo "TENANT: $OUTLOOK_TENANT_ID"
   echo "CLIENT: $OUTLOOK_CLIENT_ID"
   echo "SECRET: ${OUTLOOK_CLIENT_SECRET:0:10}..."
   ```
   None should be empty or placeholder

3. Check redirect URI matches exactly
   ```bash
   # Local development:
   OUTLOOK_REDIRECT_URI=http://localhost:8000/auth/outlook/callback
   
   # This must match EXACTLY in Azure Portal:
   # Settings → Authentication → Redirect URIs
   ```

4. Verify API permissions in Azure Portal
   - App Registrations → Your App → API permissions
   - You should have:
     - ✅ Calendars.ReadWrite (Delegated)
     - ✅ offline_access (Delegated)
   - If not granted: click "Grant admin consent"

5. Check logs for OAuth errors
   ```bash
   docker-compose logs hr_bot | grep -i oauth
   docker-compose logs hr_bot | grep -i "exchange code"
   ```

### Problem: OAuth callback URL keeps showing error page

**Check these:**

1. Is the redirect URI in Azure Portal correct?
   - Settings → Authentication → Redirect URIs
   - Should be: `http://localhost:8000/auth/outlook/callback`

2. Is the OUTLOOK_REDIRECT_URI in `.env` correct?
   ```bash
   echo $OUTLOOK_REDIRECT_URI
   # Should match what's in Azure Portal
   ```

3. Are you using production domain?
   - Redirect URI must match your actual domain
   - Can't use `localhost` in production

---

## Outlook Meetings Not Creating

### Problem: `/schedule_meeting` says "Meeting Scheduled!" but no invite appears

**Check these:**

1. Verify Outlook token is stored and valid
   ```bash
   # Check database
   docker exec hr_bot_db psql -U hrbot -d hr_bot_db -c \
     "SELECT user_id, outlook_email, outlook_access_token IS NOT NULL FROM hr_configs;"
   ```
   The `outlook_access_token` column should show `t` (true)

2. Check token hasn't expired
   ```bash
   # Automatic refresh runs every 50 minutes, but check anyway
   docker-compose logs hr_bot | grep -i "token"
   ```

3. Verify recipient email is valid and exists
   - Try scheduling with your own email first
   - Check spelling of recipient email

4. Check Outlook Calendar has correct permissions
   - In Azure Portal: App Registrations → API permissions
   - Should have: Calendars.ReadWrite

5. Check logs for Graph API errors
   ```bash
   docker-compose logs hr_bot | grep -i "create_meeting\|graph"
   ```
   Look for 403 (permission), 400 (bad request), 401 (auth failed)

---

## Scheduled Reminders Not Sending

### Problem: Quarterly/monthly reminders don't trigger

**Check these:**

1. Is the scheduler running?
   ```bash
   curl http://localhost:8000/jobs
   # Should show: quarterly_reminders, monthly_site_visit_reminder, etc.
   ```

2. Is the next_run_time in the future?
   ```bash
   curl http://localhost:8000/jobs | jq '.jobs[0].next_run'
   # Should not be null
   ```

3. Check timezone is correct in `.env`
   ```bash
   echo $TIMEZONE
   # Should be IANA format: Asia/Jerusalem, Europe/London, America/New_York, etc.
   # NOT "IST" or "GMT" (those are not unambiguous)
   ```

4. Check time in Docker container matches your machine
   ```bash
   docker exec hr_bot_db date
   # Should show current date/time
   ```

5. Verify database has user configs
   ```bash
   docker exec hr_bot_db psql -U hrbot -d hr_bot_db -c "SELECT * FROM hr_configs;"
   # Should return at least one row
   ```

6. Check APScheduler logs
   ```bash
   docker-compose logs hr_bot | grep -i scheduler
   docker-compose logs hr_bot | grep -i "send_quarterly\|send_monthly"
   ```

---

## Database Connection Errors

### Problem: "OperationalError: could not connect to server"

**Check these:**

1. Is PostgreSQL running?
   ```bash
   docker-compose ps postgres
   # Should show: "Up"
   ```

2. Wait for PostgreSQL to be ready
   ```bash
   docker-compose logs postgres | tail -20
   # Look for: "database system is ready to accept connections"
   ```

3. Verify DATABASE_URL
   ```bash
   echo $DATABASE_URL
   # Should be: postgresql://user:pass@host:5432/db
   ```

4. Try connecting directly
   ```bash
   psql postgresql://hrbot:hrbot_dev_password@localhost:5432/hr_bot_db
   # Should open interactive prompt
   ```

5. Reset database
   ```bash
   make db-reset
   # Or: docker-compose down -v && docker-compose up postgres
   ```

---

## Common Error Messages

| Error | Meaning | Fix |
|-------|---------|-----|
| `400 Bad Request` | Invalid request to Outlook | Check email format, date format |
| `401 Unauthorized` | Token invalid/expired | Re-run `/setup`, restart bot |
| `403 Forbidden` | App lacks permission | Check API permissions in Azure Portal |
| `Invalid date format` | User entered wrong format | Use `YYYY-MM-DD HH:MM` |
| `Conversation not found` | 24h conversation timeout | Start new `/schedule_meeting` |
| `Outlook not connected` | User didn't complete `/setup` | Send `/setup` to authorize |
| `User config not found` | Bot state not initialized | Send `/start` first |

---

## Debug Commands

### Quick Health Check
```bash
# All systems
curl http://localhost:8000/health && echo "✅ OK"

# Just database
docker exec hr_bot_db psql -U hrbot -d hr_bot_db -c "SELECT 1;"

# Just Telegram (check bot token)
curl -s "https://api.telegram.org/bot$TELEGRAM_TOKEN/getMe" | jq '.result.username'
```

### View Logs
```bash
# Follow all logs
docker-compose logs -f

# Just bot
docker-compose logs -f hr_bot

# Just database
docker-compose logs -f postgres

# Search for errors
docker-compose logs | grep -i error

# Last N lines
docker-compose logs --tail 50
```

### Database Queries
```bash
# Connect to database
psql $DATABASE_URL

# See all users
SELECT * FROM hr_configs;

# See scheduled meetings
SELECT * FROM scheduled_meetings;

# See active conversations
SELECT * FROM conversation_states;

# Check token expiry
SELECT user_id, outlook_token_expiry, NOW() FROM hr_configs;
```

### Restart Everything
```bash
# Clean restart
docker-compose down && docker-compose up -d

# Reset database
docker-compose down -v && docker-compose up -d

# Full clean (delete all data)
docker-compose down -v
docker system prune -a
docker-compose up -d
```

---

## Still Not Working?

1. **Collect information:**
   ```bash
   # Save logs
   docker-compose logs > logs.txt
   
   # Save config (without secrets)
   grep -v SECRET .env | grep -v PASSWORD > config.txt
   
   # Save database state
   docker exec hr_bot_db pg_dump -U hrbot hr_bot_db > db_backup.sql
   ```

2. **Check documentation:**
   - [FastAPI Docs](https://fastapi.tiangolo.com)
   - [Telegram Bot API](https://core.telegram.org/bots/api)
   - [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/api/overview)

3. **Review CLAUDE.md:**
   - Architecture decisions
   - Database schema
   - OAuth flow details

4. **Enable debug mode:**
   ```bash
   DEBUG=True LOG_LEVEL=DEBUG docker-compose up -f hr_bot
   ```
