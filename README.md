# HR Bot - Telegram HR Assistant

An AI-powered Telegram bot that acts as your HR manager assistant. Helps you manage team lunches, track employee gifts, coordinate site visits, and schedule company events.

## Features

✅ **Quarterly Reminders** - Schedule team lunches at the start of each quarter  
✅ **Gift Planning** - Quarterly reminders to check employee gifts for holidays  
✅ **Monthly Check-ins** - Prompt to meet with site managers  
✅ **Company Events** - Plan monthly company events  
✅ **Outlook Integration** - Direct calendar synchronization via Microsoft Graph API  
✅ **Scheduled Tasks** - APScheduler for timezone-aware reminders  
✅ **Async-First** - Fast, non-blocking I/O throughout  

## Tech Stack

- **FastAPI** - Web framework
- **SQLAlchemy 2.0** - ORM
- **PostgreSQL** - Database
- **python-telegram-bot** - Telegram Bot API
- **Microsoft Graph API** - Outlook integration
- **APScheduler** - Task scheduling

## Quick Start (with Docker)

### 1. Prerequisites

- Docker & Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Azure App Registration (for Outlook OAuth)

### 2. Setup

```bash
# Clone and navigate
git clone https://github.com/avishai/hr_bot.git
cd hr_bot

# Create .env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 3. Run with Docker

```bash
# Start services (PostgreSQL + Bot)
docker-compose up -d

# Verify setup
docker-compose logs hr_bot
```

Bot will be available at `http://localhost:8000`

---

## Manual Setup (without Docker)

### 1. Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Telegram Bot Token
- Azure App Registration

### 2. Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
nano .env  # Edit with your credentials
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb hr_bot_db

# Initialize schema
psql hr_bot_db < init.sql

# Or: Update DATABASE_URL in .env and let SQLAlchemy create tables on startup
DATABASE_URL=postgresql://user:password@localhost/hr_bot_db
```

## Configuration

### Telegram Bot Token

1. Open [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the token to `.env`:
   ```
   TELEGRAM_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh
   ```

### Outlook (Microsoft 365) OAuth

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **App registrations** → **New registration**
3. Set name: "HR Bot"
4. Set redirect URI: `http://localhost:8000/auth/outlook/callback` (for local dev)
5. In the app, go to **API permissions**:
   - Add permission: **Microsoft Graph** → **Delegated permissions**
   - Search for `Calendars.ReadWrite` ✅ and `offline_access` ✅
6. In **Certificates & secrets**, create a new client secret
7. Copy these values to `.env`:
   ```
   OUTLOOK_TENANT_ID=your-azure-tenant-id
   OUTLOOK_CLIENT_ID=your-azure-app-client-id
   OUTLOOK_CLIENT_SECRET=your-azure-app-secret
   OUTLOOK_REDIRECT_URI=http://localhost:8000/auth/outlook/callback
   ```

### Telegram Webhook URL

For production, set the webhook URL in `.env`:
```
TELEGRAM_WEBHOOK_URL=https://your-domain.com
```

## Running

### With Docker (Recommended)

```bash
make docker-up
```

### Manual

```bash
python -m main

# Or: uvicorn main:app --reload
```

API will be available at `http://localhost:8000`

## Usage

### Starting the Bot

1. Find your bot in Telegram search
2. Send `/start` to initialize

### Bot Commands

```
/start                                - Initialize the bot
/setup                                - Connect your Outlook calendar
/schedule_meeting email@domain.com    - Schedule a meeting
/cancel                               - Cancel current action
```

### Example Flows

#### 1. Setup (First Time)
```
You: /setup
Bot: [Connect Outlook Button]
    → Click button → Authorize with Microsoft
Bot: ✅ Outlook connected successfully!
```

#### 2. Schedule a Meeting
```
You: /schedule_meeting john.doe@company.com
Bot: 📅 Schedule Meeting
     With: john.doe@company.com
     What's the meeting topic?
     
You: Q2 Planning Discussion
Bot: 📅 When would you like to schedule this meeting?
     Format: YYYY-MM-DD HH:MM (e.g., 2026-05-15 14:30)
     
You: 2026-05-15 14:30
Bot: 📋 Confirm Meeting Details
     With: john.doe@company.com
     Topic: Q2 Planning Discussion
     Date & Time: 2026-05-15 14:30
     [✅ Confirm] [❌ Cancel]
     
You: ✅ Confirm
Bot: ✅ Meeting Scheduled!
     📅 Topic: Q2 Planning Discussion
     👤 With: john.doe@company.com
     ⏰ Date: 2026-05-15 14:30
     Invite has been sent.
```

### Scheduled Reminders

The bot automatically sends reminders based on your timezone:

- **Quarterly Lunch** (Jan 1, Apr 1, Jul 1, Oct 1 @ 09:00)
  - "🌟 It's a new quarter! Which sites need lunch arrangements?"
  - Bot creates meetings with site managers

- **Monthly Site Visits** (1st of each month @ 10:00)
  - "📍 Would you like to meet with any site managers this month?"
  - Bot schedules 1-on-1 meetings

- **Monthly Company Event** (1st of each month @ 11:00)
  - "🎉 Do you want to organize a company event this month?"
  - Bot helps plan and schedule

- **Token Refresh** (every 50 minutes)
  - Automatic: keeps your Outlook connection fresh

## Project Structure

```
hr_bot/
├── main.py                    # FastAPI app + lifespan
├── config.py                  # Pydantic settings
├── database.py                # SQLAlchemy setup
├── models/
│   ├── hr_config.py          # User configuration
│   ├── scheduled_meetings.py  # Meeting records
│   └── conversation_state.py  # Multi-step conversation tracking
├── services/
│   ├── telegram_service.py    # Bot handlers
│   ├── outlook_service.py     # Graph API integration
│   └── hr_workflow.py         # Conversation orchestration
├── tasks/
│   ├── scheduler.py           # APScheduler wrapper
│   └── hr_reminders.py        # Scheduled tasks
├── requirements.txt
├── .env.example
└── README.md
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-05-07T10:00:00",
  "scheduler_running": true
}
```

### Telegram Webhook
```bash
# Telegram will POST updates here automatically
POST /webhook/telegram
```

### Outlook OAuth Login
```bash
# Get OAuth authorization URL
curl "http://localhost:8000/auth/outlook/login?user_id=123456789"
```

**Response:**
```json
{
  "oauth_url": "https://login.microsoftonline.com/...",
  "message": "Click the link above to authorize with Outlook"
}
```

### Outlook OAuth Callback
```bash
# Handled automatically by Microsoft after user authorizes
GET /auth/outlook/callback?code=...&state=...
```

### Debug - List Jobs
```bash
curl http://localhost:8000/jobs
```

**Response:**
```json
{
  "jobs": [
    {
      "id": "quarterly_reminders",
      "name": "send_quarterly_reminders",
      "next_run": "2026-07-01T09:00:00"
    }
  ]
}
```

## Database Schema

### hr_configs
Stores user settings and Outlook tokens.

```sql
id (PK) | user_id (TG) | timezone | outlook_email | outlook_access_token | company_sites (JSON) | site_managers (JSON) | last_quarterly_reminder | last_monthly_reminder | created_at | updated_at
```

### scheduled_meetings
Records of all scheduled meetings.

```sql
id (PK) | user_id (FK) | meeting_type | event_name | scheduled_date | recipients (JSON) | outlook_event_id | status | created_at | updated_at
```

### conversation_states
Tracks multi-step conversations.

```sql
id (PK) | user_id (FK) | state_type | current_step | context_data (JSON) | created_at | expires_at | updated_at
```

## Development

### Running Tests

```bash
pytest
```

### Logging

Logs are written to console at INFO level. Set `DEBUG=True` in `.env` for verbose output.

## Deployment

### Docker

```bash
docker build -t hr-bot .
docker run -p 8000:8000 --env-file .env hr-bot
```

### Environment Variables (Production)

```
DATABASE_URL=postgresql://user:pass@prod-db:5432/hr_bot
TELEGRAM_TOKEN=<prod-token>
TELEGRAM_WEBHOOK_URL=https://hr-bot.example.com
OUTLOOK_TENANT_ID=<prod-tenant>
OUTLOOK_CLIENT_ID=<prod-client-id>
OUTLOOK_CLIENT_SECRET=<prod-secret>
OUTLOOK_REDIRECT_URI=https://hr-bot.example.com/auth/outlook/callback
DEBUG=False
```

## Contributing

See [CLAUDE.md](./CLAUDE.md) for development guidelines.

## License

Proprietary
