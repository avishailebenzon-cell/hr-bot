import logging
from datetime import datetime
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Will be set during app startup
telegram_service = None
hr_workflow = None

async def send_quarterly_reminders():
    """Send quarterly lunch reminders on 1st of Jan, Apr, Jul, Oct"""
    logger.info("Running quarterly reminder task...")

    from database import SessionLocal
    from models import HRConfig
    from services.hr_workflow import HRWorkflow

    async with SessionLocal() as db:
        try:
            configs = await db.execute(select(HRConfig))
            configs = configs.scalars().all()

            for config in configs:
                if await hr_workflow.handle_quarterly_reminder(db, config.user_id):
                    # Send message to user
                    keyboard = HRWorkflow.get_site_selection_keyboard(config.company_sites)
                    await telegram_service.send_message(
                        config.user_id,
                        "🌟 <b>It's a new quarter!</b>\n\n"
                        "Time to organize team lunches. Which sites need lunch arrangements?\n\n"
                        "Select all that apply:",
                        reply_markup=keyboard
                    )

            logger.info(f"Quarterly reminder task completed for {len(configs)} users")

        except Exception as e:
            logger.error(f"Error in quarterly reminder task: {e}", exc_info=True)

async def send_monthly_site_visit_reminder():
    """Send monthly site visit reminders on 1st of each month @ 10:00"""
    logger.info("Running monthly site visit reminder task...")

    from database import SessionLocal
    from models import HRConfig

    async with SessionLocal() as db:
        try:
            configs = await db.execute(select(HRConfig))
            configs = configs.scalars().all()

            for config in configs:
                if await hr_workflow.handle_monthly_reminder(db, config.user_id, "site_visit"):
                    # Send message to user
                    keyboard = HRWorkflow.get_yes_no_keyboard()
                    await telegram_service.send_message(
                        config.user_id,
                        "📍 <b>Monthly Check:</b>\n\n"
                        "Would you like to meet with any site managers this month?",
                        reply_markup=keyboard
                    )

            logger.info(f"Monthly site visit reminder completed for {len(configs)} users")

        except Exception as e:
            logger.error(f"Error in monthly site visit reminder task: {e}", exc_info=True)

async def send_monthly_company_event_reminder():
    """Send monthly company event reminders on 1st of each month @ 11:00"""
    logger.info("Running monthly company event reminder task...")

    from database import SessionLocal
    from models import HRConfig

    async with SessionLocal() as db:
        try:
            configs = await db.execute(select(HRConfig))
            configs = configs.scalars().all()

            for config in configs:
                if await hr_workflow.handle_monthly_reminder(db, config.user_id, "company_event"):
                    # Send message to user
                    keyboard = HRWorkflow.get_yes_no_keyboard()
                    await telegram_service.send_message(
                        config.user_id,
                        "🎉 <b>Monthly Event Planning:</b>\n\n"
                        "Do you want to organize a company event this month?",
                        reply_markup=keyboard
                    )

            logger.info(f"Monthly company event reminder completed for {len(configs)} users")

        except Exception as e:
            logger.error(f"Error in monthly company event reminder task: {e}", exc_info=True)

async def check_token_expiry():
    """Check and refresh Outlook tokens if needed"""
    logger.info("Checking token expiry...")

    from datetime import timedelta
    from database import SessionLocal
    from models import HRConfig
    from services import OutlookService

    outlook_service = OutlookService()

    async with SessionLocal() as db:
        try:
            configs = await db.execute(select(HRConfig))
            configs = configs.scalars().all()

            for config in configs:
                if not config.outlook_refresh_token or not config.outlook_token_expiry:
                    continue

                if datetime.utcnow() >= config.outlook_token_expiry - timedelta(hours=1):
                    logger.info(f"Refreshing token for user {config.user_id}...")
                    result = await outlook_service.refresh_token(config.outlook_refresh_token)

                    if result:
                        config.outlook_access_token = result["access_token"]
                        config.outlook_token_expiry = datetime.utcnow() + datetime.timedelta(
                            seconds=result.get("expires_in", 3600)
                        )
                        await db.commit()
                        logger.info(f"Token refreshed for user {config.user_id}")

            logger.info(f"Token expiry check completed")

        except Exception as e:
            logger.error(f"Error in token expiry check: {e}", exc_info=True)

def set_services(telegram: TelegramService, workflow: HRWorkflow):
    """Set service instances (called during app startup)"""
    global telegram_service, hr_workflow
    telegram_service = telegram
    hr_workflow = workflow
