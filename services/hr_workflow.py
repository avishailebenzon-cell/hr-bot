import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import HRConfig, ConversationState, ScheduledMeeting, ConversationStateType, MeetingType, MeetingStatus
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

class HRWorkflow:
    """Orchestrates HR workflows and conversation flows"""

    def __init__(self, outlook_service):
        self.outlook_service = outlook_service

    async def handle_quarterly_reminder(self, db: AsyncSession, user_id: int) -> bool:
        """Send quarterly lunch reminder and create conversation state"""
        config = await db.execute(
            select(HRConfig).where(HRConfig.user_id == user_id)
        )
        config = config.scalar_one_or_none()

        if not config:
            logger.warning(f"No config found for user {user_id}")
            return False

        # Check if already reminded this quarter
        if config.last_quarterly_reminder:
            days_since = (datetime.utcnow() - config.last_quarterly_reminder).days
            if days_since < 85:  # Less than ~3 months
                logger.info(f"User {user_id} already reminded this quarter")
                return False

        # Create conversation state
        conversation = ConversationState(
            user_id=user_id,
            state_type=ConversationStateType.QUARTERLY_LUNCH,
            current_step="awaiting_site_selection",
            context_data={"sites": config.company_sites},
        )
        db.add(conversation)
        config.last_quarterly_reminder = datetime.utcnow()
        await db.commit()

        logger.info(f"Created quarterly reminder conversation for user {user_id}")
        return True

    async def handle_monthly_reminder(
        self,
        db: AsyncSession,
        user_id: int,
        reminder_type: str
    ) -> bool:
        """Send monthly reminders (site visits or company event)"""
        config = await db.execute(
            select(HRConfig).where(HRConfig.user_id == user_id)
        )
        config = config.scalar_one_or_none()

        if not config:
            logger.warning(f"No config found for user {user_id}")
            return False

        # Check if already reminded this month
        if config.last_monthly_reminder:
            days_since = (datetime.utcnow() - config.last_monthly_reminder).days
            if days_since < 25:  # Less than ~1 month
                logger.info(f"User {user_id} already reminded this month")
                return False

        # Determine conversation type based on hour (avoid sending both at once)
        state_type = (
            ConversationStateType.MONTHLY_SITE_VISIT
            if reminder_type == "site_visit"
            else ConversationStateType.MONTHLY_COMPANY_EVENT
        )

        conversation = ConversationState(
            user_id=user_id,
            state_type=state_type,
            current_step="awaiting_confirmation",
            context_data={},
        )
        db.add(conversation)
        config.last_monthly_reminder = datetime.utcnow()
        await db.commit()

        logger.info(f"Created monthly reminder conversation for user {user_id}: {reminder_type}")
        return True

    async def handle_quarterly_lunch_response(
        self,
        db: AsyncSession,
        user_id: int,
        selected_sites: list[str],
    ) -> None:
        """Handle user's selected sites for quarterly lunches"""
        config = await db.execute(
            select(HRConfig).where(HRConfig.user_id == user_id)
        )
        config = config.scalar_one_or_none()

        if not config:
            return

        conversation = await db.execute(
            select(ConversationState).where(
                ConversationState.user_id == user_id,
                ConversationState.state_type == ConversationStateType.QUARTERLY_LUNCH,
            )
        )
        conversation = conversation.scalar_one_or_none()

        if not conversation:
            return

        # Update conversation to next step
        conversation.current_step = "awaiting_dates"
        conversation.context_data = {"selected_sites": selected_sites}
        await db.commit()

        logger.info(f"User {user_id} selected sites for quarterly lunch: {selected_sites}")

    async def schedule_meeting(
        self,
        db: AsyncSession,
        user_id: int,
        event_name: str,
        start_time: datetime,
        recipients: list[str],
        meeting_type: MeetingType = MeetingType.CUSTOM,
        duration_minutes: int = 60,
    ) -> Optional[str]:
        """Schedule a meeting in Outlook and create record"""
        config = await db.execute(
            select(HRConfig).where(HRConfig.user_id == user_id)
        )
        config = config.scalar_one_or_none()

        if not config or not config.outlook_access_token:
            logger.warning(f"User {user_id} not properly configured for Outlook")
            return None

        # Create in Outlook
        end_time = start_time + timedelta(minutes=duration_minutes)
        event_id = await self.outlook_service.create_meeting(
            config,
            title=event_name,
            start_time=start_time,
            end_time=end_time,
            recipients=recipients,
        )

        if not event_id:
            logger.error(f"Failed to create meeting in Outlook for user {user_id}")
            return None

        # Create database record
        meeting = ScheduledMeeting(
            user_id=user_id,
            meeting_type=meeting_type,
            event_name=event_name,
            scheduled_date=start_time,
            duration_minutes=duration_minutes,
            recipients=recipients,
            outlook_event_id=event_id,
            status=MeetingStatus.SCHEDULED,
        )
        db.add(meeting)
        await db.commit()

        logger.info(f"Scheduled meeting '{event_name}' for user {user_id}")
        return event_id

    @staticmethod
    def get_site_selection_keyboard(sites: list[str]) -> InlineKeyboardMarkup:
        """Generate inline keyboard for site selection"""
        buttons = []
        for site in sites:
            buttons.append([InlineKeyboardButton(site, callback_data=f"site_{site}")])
        buttons.append([InlineKeyboardButton("Done", callback_data="sites_done")])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def get_yes_no_keyboard() -> InlineKeyboardMarkup:
        """Generate yes/no keyboard"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes", callback_data="response_yes"),
                InlineKeyboardButton("❌ No", callback_data="response_no"),
            ]
        ])
