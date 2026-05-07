import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

class TelegramService:
    """Manages Telegram bot interactions"""

    def __init__(self, token: str):
        self.token = token
        self.app: Optional[Application] = None
        self._handlers = None

    async def initialize(self, outlook_service=None, hr_workflow=None):
        """Initialize the Telegram application (call during app startup)"""
        self.app = Application.builder().token(self.token).build()

        # Initialize handlers if services are provided
        if outlook_service and hr_workflow:
            from services.telegram_handlers import TelegramHandlers
            self._handlers = TelegramHandlers(outlook_service, hr_workflow)

        self._register_handlers()

    def _register_handlers(self):
        """Register command and message handlers"""
        self.app.add_handler(CommandHandler("start", self._handle_start))
        self.app.add_handler(CommandHandler("setup", self._handle_setup))
        self.app.add_handler(CommandHandler("schedule_meeting", self._handle_schedule_meeting))
        self.app.add_handler(CommandHandler("cancel", self._handle_cancel))
        self.app.add_handler(CallbackQueryHandler(self._handle_button_click))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        user_id = update.effective_user.id
        logger.info(f"User {user_id} started bot")

        await update.message.reply_text(
            "👋 Hi! I'm your HR Assistant. I'll help you:\n\n"
            "📋 Schedule team lunches quarterly\n"
            "🎁 Remind you about employee gifts\n"
            "📍 Track monthly site manager meetings\n"
            "🎉 Organize company events\n\n"
            "Use /setup to configure me first!"
        )

    async def _handle_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /setup command"""
        user_id = update.effective_user.id
        logger.info(f"User {user_id} started setup")

        # Get OAuth URL from callback endpoint
        oauth_link = f"https://your-domain.com/auth/outlook/login?user_id={user_id}"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Connect Outlook", url=oauth_link)],
        ])

        await update.message.reply_text(
            "🔧 <b>Setup - Connect Outlook Calendar</b>\n\n"
            "Click the button below to authorize access to your Outlook calendar. "
            "This will allow me to schedule meetings for you.",
            reply_markup=keyboard
        )

    async def _handle_schedule_meeting(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /schedule_meeting command"""
        user_id = update.effective_user.id
        logger.info(f"User {user_id} requested meeting scheduling")

        if not context.args:
            await update.message.reply_text(
                "Usage: /schedule_meeting <email@domain.com>\n\n"
                "Example: /schedule_meeting john.doe@company.com"
            )
            return

        recipient_email = context.args[0]
        context.user_data["meeting_recipient"] = recipient_email
        context.user_data["state"] = "awaiting_meeting_topic"

        await update.message.reply_text(
            f"📅 Scheduling meeting with {recipient_email}\n\n"
            "What's the meeting topic?"
        )

    async def _handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /cancel command"""
        user_id = update.effective_user.id
        logger.info(f"User {user_id} cancelled current action")

        context.user_data.clear()
        await update.message.reply_text(
            "❌ Cancelled. What can I help you with?\n\n"
            "Use /schedule_meeting to schedule a meeting\n"
            "or wait for my periodic reminders."
        )

    async def _handle_button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline button clicks"""
        user_id = update.effective_user.id
        button_data = update.callback_query.data

        logger.info(f"User {user_id} clicked button: {button_data}")

        # Import here to avoid circular imports
        from services.telegram_handlers import TelegramHandlers
        if not hasattr(self, '_handlers'):
            return  # Handlers not initialized yet

        await self._handlers.handle_button_click(update, context, user_id, button_data)

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle general text messages (for multi-step conversations)"""
        user_id = update.effective_user.id
        text = update.message.text

        logger.info(f"User {user_id} sent text: {text[:50]}...")

        # Import here to avoid circular imports
        from services.telegram_handlers import TelegramHandlers
        if not hasattr(self, '_handlers'):
            await update.message.reply_text("Bot is not fully initialized yet. Try again in a moment.")
            return

        await self._handlers.handle_schedule_meeting_response(
            update, context, user_id, text
        )

    async def send_message(self, user_id: int, text: str, reply_markup=None) -> None:
        """Send a message to user (for scheduled reminders)"""
        if not self.app:
            logger.error("Telegram app not initialized")
            return

        try:
            await self.app.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Sent message to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")

    async def set_webhook(self, webhook_url: str) -> None:
        """Set up webhook for Telegram updates"""
        if not self.app:
            logger.error("Telegram app not initialized")
            return

        try:
            await self.app.bot.set_webhook(
                url=f"{webhook_url}/webhook/telegram",
                allowed_updates=["message", "callback_query"]
            )
            logger.info(f"Webhook set to {webhook_url}")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")

    async def process_update(self, update_data: dict) -> None:
        """Process a Telegram update (from webhook)"""
        if not self.app:
            logger.error("Telegram app not initialized")
            return

        try:
            from telegram import Update as TelegramUpdate
            update = TelegramUpdate.de_json(update_data, self.app.bot)
            if update:
                await self.app.process_update(update)
        except Exception as e:
            logger.error(f"Failed to process update: {e}")
