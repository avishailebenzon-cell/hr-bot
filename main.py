import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from apscheduler.triggers.cron import CronTrigger

from config import get_settings
from database import init_db, close_db
from services import TelegramService, OutlookService
from services.hr_workflow import HRWorkflow
from tasks.scheduler import task_scheduler
from tasks import hr_reminders

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize services (singleton instances)
telegram_service = TelegramService(settings.telegram_token)
outlook_service = OutlookService()
hr_workflow = HRWorkflow(outlook_service)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app startup and shutdown"""
    logger.info("Starting HR Bot application...")

    # Initialize database
    await init_db()

    # Initialize Telegram bot with services
    await telegram_service.initialize(outlook_service, hr_workflow)
    logger.info("Telegram bot initialized")

    # Set service instances for scheduled tasks
    hr_reminders.set_services(telegram_service, hr_workflow)

    # Register scheduled tasks
    logger.info("Registering scheduled tasks...")

    # Quarterly reminders: 1st of Jan, Apr, Jul, Oct @ 09:00
    task_scheduler.add_job(
        hr_reminders.send_quarterly_reminders,
        CronTrigger(month="1,4,7,10", day=1, hour=9, minute=0),
        job_id="quarterly_reminders"
    )

    # Monthly site visit reminders: 1st of each month @ 10:00
    task_scheduler.add_job(
        hr_reminders.send_monthly_site_visit_reminder,
        CronTrigger(day=1, hour=10, minute=0),
        job_id="monthly_site_visit_reminder"
    )

    # Monthly company event reminders: 1st of each month @ 11:00
    task_scheduler.add_job(
        hr_reminders.send_monthly_company_event_reminder,
        CronTrigger(day=1, hour=11, minute=0),
        job_id="monthly_company_event_reminder"
    )

    # Token refresh check: every 50 minutes
    task_scheduler.add_job(
        hr_reminders.check_token_expiry,
        CronTrigger(minute="*/50"),
        job_id="token_expiry_check"
    )

    # Start scheduler
    await task_scheduler.start()

    logger.info("HR Bot startup complete")

    yield

    # Shutdown
    logger.info("Shutting down HR Bot...")
    await task_scheduler.stop()
    await close_db()
    logger.info("HR Bot shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="HR Bot",
    description="AI-powered HR Assistant for Telegram",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "scheduler_running": task_scheduler.scheduler.running if hasattr(task_scheduler, 'scheduler') else False,
    }

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Telegram webhook endpoint"""
    try:
        data = await request.json()
        logger.info(f"Received Telegram update: {data.get('update_id')}")

        # Process update through Telegram service
        await telegram_service.process_update(data)

        return JSONResponse({"ok": True})

    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}", exc_info=True)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)

@app.get("/auth/outlook/login")
async def outlook_login(user_id: int):
    """Redirect user to Microsoft OAuth with Telegram user_id as state"""
    import secrets

    if not user_id:
        return {"error": "user_id is required"}, status_code=400

    # Use user_id as state (maps token back to Telegram user)
    oauth_url = OutlookService.get_oauth_url(state=str(user_id))

    return {
        "oauth_url": oauth_url,
        "message": "Click the link above to authorize with Outlook"
    }

@app.get("/auth/outlook/callback")
async def outlook_callback(code: str, state: str = None):
    """Handle OAuth callback from Microsoft"""
    from database import SessionLocal
    from models import HRConfig

    if not code:
        return {"error": "No authorization code received"}, status_code=400

    if not state:
        return {"error": "Invalid state parameter"}, status_code=400

    try:
        user_id = int(state)
    except (ValueError, TypeError):
        return {"error": "Invalid state parameter (user_id)"}, status_code=400

    try:
        # Exchange code for token
        token_data = await OutlookService.exchange_code_for_token(code)

        if not token_data:
            return {
                "status": "error",
                "message": "Failed to exchange authorization code for token"
            }, status_code=400

        # Store token in HRConfig
        async with SessionLocal() as db:
            config = await db.execute(
                __import__('sqlalchemy').select(HRConfig).where(HRConfig.user_id == user_id)
            )
            config = config.scalar_one_or_none()

            if not config:
                # Create new config for first-time users
                config = HRConfig(
                    user_id=user_id,
                    timezone=settings.timezone,
                )
                db.add(config)

            # Store tokens
            config.outlook_access_token = token_data.get("access_token")
            config.outlook_refresh_token = token_data.get("refresh_token")

            # Calculate expiry time
            expires_in = token_data.get("expires_in", 3600)
            from datetime import timedelta
            config.outlook_token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

            # Get user info from Outlook
            user_info = await outlook_service.get_user_info(config.outlook_access_token)
            if user_info:
                config.outlook_email = user_info.get("mail") or user_info.get("userPrincipalName")

            await db.commit()

        logger.info(f"OAuth successful for user {user_id}")

        # Send confirmation to Telegram
        await telegram_service.send_message(
            user_id,
            "✅ <b>Outlook connected successfully!</b>\n\n"
            "I can now schedule meetings on your calendar. Use /schedule_meeting to get started!"
        )

        return {
            "status": "success",
            "message": "Successfully connected to Outlook! Check your Telegram bot for confirmation."
        }

    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}", exc_info=True)
        return {"error": str(e)}, status_code=500

@app.get("/jobs")
async def list_jobs():
    """List all scheduled jobs (for debugging)"""
    jobs = task_scheduler.get_jobs()
    return {
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in jobs
        ]
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
