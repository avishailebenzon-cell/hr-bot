import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select
from database import SessionLocal
from models import HRConfig, ConversationState, ConversationStateType, ScheduledMeeting, MeetingType
from services.hr_workflow import HRWorkflow

logger = logging.getLogger(__name__)

class TelegramHandlers:
    """Grouped Telegram message handlers"""

    def __init__(self, outlook_service, hr_workflow: HRWorkflow):
        self.outlook_service = outlook_service
        self.hr_workflow = hr_workflow

    async def handle_schedule_meeting_response(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        message_text: str,
    ) -> None:
        """Handle user responses during schedule_meeting flow"""
        state_type = ConversationStateType.CUSTOM_MEETING

        async with SessionLocal() as db:
            # Get or create conversation state
            conversation = await db.execute(
                select(ConversationState).where(
                    ConversationState.user_id == user_id,
                    ConversationState.state_type == state_type,
                )
            )
            conversation = conversation.scalar_one_or_none()

            if not conversation:
                # No active conversation - start fresh
                recipient_email = context.user_data.get("meeting_recipient")

                if not recipient_email:
                    await update.message.reply_text(
                        "❌ Error: No recipient email found.\n\n"
                        "Use: /schedule_meeting email@domain.com"
                    )
                    return

                # Create conversation state
                conversation = ConversationState(
                    user_id=user_id,
                    state_type=state_type,
                    current_step="awaiting_meeting_topic",
                    context_data={"recipient_email": recipient_email},
                )
                db.add(conversation)
                await db.commit()

                await update.message.reply_text(
                    f"📅 <b>Schedule Meeting</b>\n\n"
                    f"With: <code>{recipient_email}</code>\n\n"
                    f"What's the meeting topic?"
                )
                return

            current_step = conversation.current_step
            context_data = conversation.context_data or {}

            # Handle different steps
            if current_step == "awaiting_meeting_topic":
                context_data["meeting_topic"] = message_text
                conversation.current_step = "awaiting_meeting_date"
                await db.commit()

                await update.message.reply_text(
                    "📅 When would you like to schedule this meeting?\n\n"
                    "Format: <code>YYYY-MM-DD HH:MM</code>\n"
                    "Example: <code>2026-05-15 14:30</code>"
                )

            elif current_step == "awaiting_meeting_date":
                try:
                    meeting_date = datetime.strptime(message_text.strip(), "%Y-%m-%d %H:%M")
                except ValueError:
                    await update.message.reply_text(
                        "❌ Invalid date format.\n\n"
                        "Please use: <code>YYYY-MM-DD HH:MM</code>\n"
                        "Example: <code>2026-05-15 14:30</code>"
                    )
                    return

                context_data["meeting_date"] = message_text
                conversation.current_step = "awaiting_confirmation"
                await db.commit()

                # Show confirmation
                recipient = context_data.get("recipient_email")
                topic = context_data.get("meeting_topic")

                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Confirm", callback_data="meeting_confirm"),
                        InlineKeyboardButton("❌ Cancel", callback_data="meeting_cancel"),
                    ]
                ])

                await update.message.reply_text(
                    f"📋 <b>Confirm Meeting Details</b>\n\n"
                    f"<b>With:</b> <code>{recipient}</code>\n"
                    f"<b>Topic:</b> {topic}\n"
                    f"<b>Date & Time:</b> {message_text}\n\n"
                    f"Is this correct?",
                    reply_markup=keyboard
                )

            else:
                await update.message.reply_text(
                    "I didn't understand that.\n\n"
                    "Use /schedule_meeting email@domain.com to book a meeting."
                )

    async def handle_meeting_confirmation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        confirm: bool,
    ) -> None:
        """Handle meeting confirmation"""
        query = update.callback_query
        await query.answer()

        async with SessionLocal() as db:
            # Get conversation
            conversation = await db.execute(
                select(ConversationState).where(
                    ConversationState.user_id == user_id,
                    ConversationState.state_type == ConversationStateType.CUSTOM_MEETING,
                )
            )
            conversation = conversation.scalar_one_or_none()

            if not conversation:
                await query.edit_message_text("❌ Conversation not found. Use /schedule_meeting to start over.")
                return

            if not confirm:
                # Delete conversation and cancel
                await db.delete(conversation)
                await db.commit()
                await query.edit_message_text("❌ Meeting cancelled.")
                return

            # Proceed with booking
            context_data = conversation.context_data or {}
            recipient_email = context_data.get("recipient_email")
            meeting_topic = context_data.get("meeting_topic")
            date_str = context_data.get("meeting_date")

            # Parse date
            try:
                meeting_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            except ValueError:
                await query.edit_message_text("❌ Invalid date format. Please try again.")
                return

            # Get user config
            config = await db.execute(
                select(HRConfig).where(HRConfig.user_id == user_id)
            )
            config = config.scalar_one_or_none()

            if not config or not config.outlook_access_token:
                await query.edit_message_text(
                    "❌ Outlook not connected. Use /setup to authorize first."
                )
                return

            # Schedule meeting
            event_id = await self.hr_workflow.schedule_meeting(
                db,
                user_id=user_id,
                event_name=meeting_topic,
                start_time=meeting_date,
                recipients=[recipient_email],
                meeting_type=MeetingType.CUSTOM,
            )

            # Clean up conversation
            await db.delete(conversation)
            await db.commit()

            if event_id:
                await query.edit_message_text(
                    f"✅ <b>Meeting Scheduled!</b>\n\n"
                    f"📅 Topic: {meeting_topic}\n"
                    f"👤 With: <code>{recipient_email}</code>\n"
                    f"⏰ Date: {date_str}\n\n"
                    f"Invite has been sent to {recipient_email}."
                )
            else:
                await query.edit_message_text(
                    "❌ Failed to schedule meeting in Outlook. Please try again."
                )

    async def handle_button_click(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        button_data: str,
    ) -> None:
        """Handle inline button clicks"""
        query = update.callback_query
        await query.answer()

        if button_data == "meeting_confirm":
            await self.handle_meeting_confirmation(update, context, user_id, confirm=True)

        elif button_data == "meeting_cancel":
            await self.handle_meeting_confirmation(update, context, user_id, confirm=False)

        elif button_data.startswith("site_"):
            # Site selection for quarterly lunches
            site = button_data.replace("site_", "")
            context.user_data["selected_sites"] = context.user_data.get("selected_sites", [])
            if site not in context.user_data["selected_sites"]:
                context.user_data["selected_sites"].append(site)
            await query.edit_message_text(
                f"✅ Selected: {', '.join(context.user_data['selected_sites'])}\n\n"
                "Add more sites or click Done."
            )

        elif button_data == "sites_done":
            selected_sites = context.user_data.get("selected_sites", [])
            if not selected_sites:
                await query.answer("Please select at least one site.", show_alert=True)
                return

            await query.edit_message_text(
                f"Great! I've selected: {', '.join(selected_sites)}\n\n"
                "When would you like to schedule these lunches?"
            )

        elif button_data in ["response_yes", "response_no"]:
            # Yes/No responses
            context.user_data["response"] = button_data == "response_yes"
            await query.edit_message_text(
                "Got it! ✅" if context.user_data["response"] else "No problem. ❌"
            )
