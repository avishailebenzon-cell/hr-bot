# HR Bot - Development Guide

## Project Overview

Telegram bot that acts as an HR assistant for managing team lunches, gifts, site visits, and company events. Integrates with Microsoft Outlook for calendar management.

## Architecture

### Technology Stack
- **Framework**: FastAPI (async web framework)
- **ORM**: SQLAlchemy 2.0 with Pydantic models
- **Database**: PostgreSQL
- **Telegram**: python-telegram-bot v20+
- **Outlook**: Microsoft Graph API via httpx
- **Scheduling**: APScheduler

### Directory Structure
```
hr_bot/
├── main.py                      # FastAPI app + lifespan
├── config.py                    # Pydantic BaseSettings
├── database.py                  # SQLAlchemy setup
├── models/                      # ORM models
│   ├── hr_config.py            # User settings
│   ├── scheduled_meetings.py    # Meeting records
│   └── conversation_state.py    # Conversation tracking
├── services/                    # Business logic
│   ├── telegram_service.py      # Bot handlers
│   ├── outlook_service.py       # Graph API integration
│   └── hr_workflow.py           # Conversation flows
├── tasks/                       # Background jobs
│   ├── scheduler.py             # APScheduler wrapper
│   └── hr_reminders.py          # Scheduled tasks
└── api/                         # API endpoints (future)
```

## Database Design

### Core Tables

1. **hr_configs**: User settings & Outlook tokens
   - `user_id` (Telegram ID, unique)
   - `timezone` (IANA timezone string)
   - `outlook_email`, `outlook_access_token`, `outlook_refresh_token`
   - `company_sites` (JSON list)
   - `site_managers` (JSON dict: site → email)
   - `last_quarterly_reminder`, `last_monthly_reminder` (timestamps)

2. **scheduled_meetings**: Meeting records
   - `user_id` (FK)
   - `meeting_type` (enum: TEAM_LUNCH, SITE_VISIT, COMPANY_EVENT, CUSTOM)
   - `event_name`, `scheduled_date`, `recipients` (JSON)
   - `outlook_event_id` (from Microsoft Graph)
   - `status` (enum: DRAFT, SCHEDULED, CANCELLED, COMPLETED)

3. **conversation_states**: Multi-step conversation tracking
   - `user_id` (FK)
   - `state_type` (enum: QUARTERLY_LUNCH, MONTHLY_SITE_VISIT, etc)
   - `current_step` (string: e.g., "awaiting_confirmation")
   - `context_data` (JSON: persisted conversation context)
   - `expires_at` (24-hour timeout)

## Telegram Bot Flows

### Flow 1: Quarterly Reminder (1st of Jan, Apr, Jul, Oct @ 09:00)
1. Bot sends: "🌟 It's a new quarter! Which sites need lunch?"
2. User selects sites (inline buttons)
3. Bot: "When would you like to schedule them?"
4. User provides dates
5. Bot creates meetings in Outlook with site_managers

### Flow 2: Quarterly Gift Check
1. Bot sends: "🎁 Check employee gifts for upcoming holidays?"
2. User: Yes/No
3. If yes: schedule 1-on-1 with user in Outlook

### Flow 3: Monthly Site Visit Check (1st of month @ 10:00)
1. Bot: "Meet with any site managers this month?"
2. User: picks managers
3. Bot: "Preferred date/time?"
4. Bot creates meetings in Outlook

### Flow 4: Monthly Company Event (1st of month @ 11:00)
1. Bot: "Organize a company event?"
2. User: confirms
3. Bot: "Event type? Date? Location?"
4. Bot creates meeting with all attendees

### Flow 5: Ad-hoc Meeting (User-initiated)
1. User: `/schedule_meeting email@domain.com`
2. Bot: "Meeting topic?"
3. User types topic
4. Bot: "Date and time?"
5. Bot creates meeting in Outlook

## API Design

### Endpoints

```
GET /health                   # Service status
POST /webhook/telegram        # Telegram updates (webhook)
GET /auth/outlook/login       # OAuth redirect URL
GET /auth/outlook/callback    # OAuth callback handler
GET /jobs                     # List scheduled jobs (debug)
```

### Response Format
All endpoints return JSON. Telegram webhook returns `{"ok": true}`.

## Configuration

Environment variables via `.env`:
```
DATABASE_URL=postgresql://...
TELEGRAM_TOKEN=...
OUTLOOK_TENANT_ID=...
OUTLOOK_CLIENT_ID=...
OUTLOOK_CLIENT_SECRET=...
OUTLOOK_REDIRECT_URI=...
TIMEZONE=Asia/Jerusalem
DEBUG=False
LOG_LEVEL=INFO
```

## Scheduled Tasks

Using APScheduler with CronTrigger:

1. **Quarterly reminders** (1st of Jan, Apr, Jul, Oct @ 09:00)
   - Calls: `send_quarterly_reminders()`
   - Sends bot message to all users
   - Creates ConversationState for multi-step flow

2. **Monthly site visit** (1st of each month @ 10:00)
   - Calls: `send_monthly_site_visit_reminder()`
   - Asks about manager meetings

3. **Monthly company event** (1st of each month @ 11:00)
   - Calls: `send_monthly_company_event_reminder()`
   - Asks about company event

4. **Token refresh** (every 50 minutes)
   - Calls: `check_token_expiry()`
   - Refreshes Outlook tokens automatically

## Development Workflow

### Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
```

### Running
```bash
python -m main
# Or: uvicorn main:app --reload
```

### Testing
```bash
pytest
pytest -v --cov
```

## Code Standards

### Async Patterns
- All I/O is async (`async def`, `await`)
- FastAPI dependency injection for DB sessions
- `async with` for resource cleanup (httpx clients, DB sessions)

### Error Handling
- HTTPException for API errors
- Try-except with logging in services
- Never let exceptions bubble without logging

### Logging
```python
import logging
logger = logging.getLogger(__name__)
logger.info("important event")
logger.error("error occurred", exc_info=True)
```

### Type Hints
- Full Python 3.10+ type annotations
- Separate SQLAlchemy models from Pydantic schemas (future)
- Optional[T] for nullable fields

## Outlook Integration

### OAuth Flow
1. User clicks `/setup`
2. Bot sends login URL via `OutlookService.get_oauth_url()`
3. User logs in → redirect to `/auth/outlook/callback?code=...`
4. Exchange code for token → store in HRConfig
5. Token auto-refreshes every 50 minutes

### Meeting Creation
```python
event_id = await outlook_service.create_meeting(
    user_config=config,
    title="Team Lunch - Ness Ziona",
    start_time=datetime(...),
    recipients=["manager@company.com"],
)
# Returns: outlook_event_id from Microsoft Graph
```

## Telegram Webhook Setup

For production, set webhook URL:
```python
await telegram_service.set_webhook("https://your-domain.com")
```

Then Telegram will POST updates to `/webhook/telegram` endpoint.

## Future Enhancements

1. **User Settings UI**: Web dashboard to manage company sites, managers
2. **Availability Checking**: Use Outlook's `getSchedule` to suggest free slots
3. **Meeting Templates**: Predefined meeting templates (lunch format, event checklist)
4. **Approval Workflow**: Admin approval for scheduled meetings
5. **Analytics**: Track reminder response rates, meeting attendance
6. **Multi-language**: Support Hebrew, English
7. **Polling Fallback**: If webhook fails, use bot polling
8. **Database Migrations**: Alembic for schema versioning

## Deployment

### Docker
```bash
docker build -t hr-bot .
docker run -p 8000:8000 --env-file .env hr-bot
```

### Production Checklist
- [ ] Set `DEBUG=False`
- [ ] Configure real `TELEGRAM_WEBHOOK_URL`
- [ ] Set `LOG_LEVEL=WARNING`
- [ ] Database backups configured
- [ ] Token encryption in place (currently plain text)
- [ ] HTTPS for OAuth callback
- [ ] Health checks passing
- [ ] Rate limiting configured

## Important Notes

- **No hard deletes**: Use enum `status` fields for soft deletes
- **Idempotent reminders**: Check `last_*_reminder` before sending
- **Timezone-aware**: All times stored as UTC, converted to user's timezone
- **Conversation timeout**: 24-hour expiry on ConversationState
- **Token security**: TODO - encrypt Outlook tokens at rest
- **Error recovery**: Scheduled tasks log errors but continue running

## Testing Strategy

- **Unit**: Model definitions, timezone calculations
- **Integration**: Telegram handlers with mocked services
- **E2E**: Full flow from reminder to Outlook event (with test database)

Use `pytest-asyncio` for async tests.

## Troubleshooting

### Bot not responding
- Check `TELEGRAM_TOKEN` is correct
- Verify webhook URL is accessible
- Check logs for errors

### Outlook meetings not creating
- Verify `OUTLOOK_ACCESS_TOKEN` is valid
- Check token hasn't expired (should auto-refresh)
- Ensure Outlook app has `Calendars.ReadWrite` permission

### Reminders not sending
- Check APScheduler is running (`/jobs` endpoint)
- Verify cron expressions (wrong timezone?)
- Check database has user configs

## References

- [FastAPI Docs](https://fastapi.tiangolo.com)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [python-telegram-bot](https://python-telegram-bot.readthedocs.io)
- [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/api/overview)
- [APScheduler](https://apscheduler.readthedocs.io)
