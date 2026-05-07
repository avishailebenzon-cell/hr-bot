"""
Simple Telegram bot - polling mode (no database needed for initial testing)
"""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Telegram token
TOKEN = "8769368501:AAEKmOZN47ELGOwddJHIVjijO1VjNdDyBh8"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.first_name}) started bot")

    await update.message.reply_html(
        f"👋 שלום {user.first_name}!\n\n"
        "אני מנהלת משאבי אנוש שלך. אני יכולה לעזור לך:\n\n"
        "📋 לתאם ארוחות משותפות\n"
        "🎁 להזכיר לך על מתנות לעובדים\n"
        "📍 לעקוב אחרי פגישות עם מנהלי אתרים\n"
        "🎉 לתכנן אירועי חברה\n\n"
        "שתמש ב-/help להצגת כל הפקודות"
    )

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /setup command"""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested setup")

    await update.message.reply_html(
        "🔧 <b>הגדרה - חבר יומן Outlook</b>\n\n"
        "כדי להשתמש בשילוב עם Outlook:\n"
        "1. הגדר Azure App Registration\n"
        "2. הוסף משתנים OUTLOOK_* ל-.env\n"
        "3. הפעל מחדש את הבוט\n\n"
        "בינתיים, נסה: /schedule_meeting test@example.com"
    )

async def schedule_meeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /schedule_meeting command"""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "שימוש: /schedule_meeting email@domain.com\n\n"
            "דוגמה: /schedule_meeting john.doe@company.com"
        )
        return

    email = context.args[0]
    logger.info(f"User {user_id} scheduling with {email}")

    await update.message.reply_text(
        f"📅 <b>תאם פגישה</b>\n\n"
        f"עם: <code>{email}</code>\n\n"
        f"(זרימה מלאה תגיע בקרוב לאחר הגדרת מסד הנתונים)",
        parse_mode="HTML"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    await update.message.reply_html(
        "<b>פקודות זמינות:</b>\n\n"
        "/start - התחל עם הבוט\n"
        "/setup - חבר Outlook (קרוב)\n"
        "/schedule_meeting &lt;email&gt; - תאם פגישה\n"
        "/help - הצג הודעה זו"
    )

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setup", setup))
    application.add_handler(CommandHandler("schedule_meeting", schedule_meeting))
    application.add_handler(CommandHandler("help", help_command))

    logger.info("🚀 הבוט מתחיל בפולינג...")
    logger.info("מחכה להודעות...")

    # Run the bot with polling
    application.run_polling()

if __name__ == "__main__":
    main()
