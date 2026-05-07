"""
Simple Telegram bot - polling mode (no database needed for initial testing)
"""
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from services.wellness_service import WellnessService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Telegram token
TOKEN = "8769368501:AAEKmOZN47ELGOwddJHIVjijO1VjNdDyBh8"

# Wellness service (will be initialized in main)
wellness_service = None
wellness_file_id = None

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
        "🎉 לתכנן אירועי חברה\n"
        "💚 לענות שאלות על תוכנית הרווחה\n\n"
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

async def wellness_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wellness_info command - Answer questions about wellness plan"""
    global wellness_file_id

    if not context.args:
        await update.message.reply_text(
            "שימוש: /wellness_info שאלה בעברית\n\n"
            "דוגמאות:\n"
            "/wellness_info מה התקציב לחנוכה?\n"
            "/wellness_info מתי מתוכננת ארוחת הצהוריים?"
        )
        return

    if not wellness_service or not wellness_file_id:
        await update.message.reply_text(
            "❌ שירות הרווחה אינו זמין כרגע. בדוק שהתוכן הטעון בעדכון."
        )
        return

    question = " ".join(context.args)
    user_id = update.effective_user.id

    try:
        await update.message.reply_text("⏳ מעבד את השאלה...")

        answer = await wellness_service.answer_question(
            question=question,
            file_id=wellness_file_id,
            context=f"User ID: {user_id}"
        )

        await update.message.reply_text(
            f"💚 <b>תשובה:</b>\n\n{answer}",
            parse_mode="HTML"
        )
        logger.info(f"User {user_id} asked wellness question: {question}")

    except Exception as e:
        logger.error(f"Error answering wellness question: {str(e)}")
        await update.message.reply_text(
            f"❌ שגיאה בעיבוד השאלה: {str(e)}"
        )

async def wellness_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wellness_reminders command - Show upcoming wellness activities"""
    global wellness_file_id

    if not wellness_service or not wellness_file_id:
        await update.message.reply_text(
            "❌ שירות הרווחה אינו זמין כרגע."
        )
        return

    try:
        await update.message.reply_text("⏳ טוען פעילויות קרובות...")

        answer = await wellness_service.answer_question(
            question="מהן 5 הפעילויות הקרובות ביותר בתוכנית הרווחה עם התאריכים שלהן?",
            file_id=wellness_file_id
        )

        await update.message.reply_text(
            f"📅 <b>פעילויות קרובות:</b>\n\n{answer}",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error fetching wellness reminders: {str(e)}")
        await update.message.reply_text(
            f"❌ שגיאה בטעינת הפעילויות: {str(e)}"
        )

async def wellness_create_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /wellness_create_new command - Generate new wellness plan"""
    global wellness_file_id

    if len(context.args) < 2:
        await update.message.reply_text(
            "שימוש: /wellness_create_new שנה שינויים\n\n"
            "דוגמה:\n"
            "/wellness_create_new 2027 להוסיף 50 שח לכל מתנה"
        )
        return

    if not wellness_service or not wellness_file_id:
        await update.message.reply_text(
            "❌ שירות הרווחה אינו זמין כרגע."
        )
        return

    year = context.args[0]
    changes = " ".join(context.args[1:])

    try:
        await update.message.reply_text("⏳ יוצר תוכנית חדשה...")

        plan = await wellness_service.generate_new_plan(
            file_id=wellness_file_id,
            year=year,
            changes=changes
        )

        await update.message.reply_text(
            f"✅ <b>תוכנית חדשה לשנת {year}:</b>\n\n{plan}",
            parse_mode="HTML"
        )
        logger.info(f"Generated new wellness plan for {year}")

    except Exception as e:
        logger.error(f"Error generating wellness plan: {str(e)}")
        await update.message.reply_text(
            f"❌ שגיאה ביצירת התוכנית: {str(e)}"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    await update.message.reply_html(
        "<b>פקודות זמינות:</b>\n\n"
        "/start - התחל עם הבוט\n"
        "/setup - חבר Outlook (קרוב)\n"
        "/schedule_meeting &lt;email&gt; - תאם פגישה\n"
        "/wellness_info &lt;שאלה&gt; - שאל על תוכנית הרווחה\n"
        "/wellness_reminders - הצג פעילויות קרובות\n"
        "/wellness_create_new &lt;שנה&gt; &lt;שינויים&gt; - צור תוכנית חדשה\n"
        "/help - הצג הודעה זו"
    )

async def post_init(application: Application) -> None:
    """Initialize wellness service after bot startup."""
    global wellness_service, wellness_file_id

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    wellness_file_path = os.getenv("WELLNESS_FILE_PATH")

    if anthropic_key and wellness_file_path:
        try:
            wellness_service = WellnessService(api_key=anthropic_key)
            logger.info("✅ WellnessService initialized")

            # Upload wellness file
            wellness_file_id = await wellness_service.upload_file(wellness_file_path)
            logger.info(f"✅ Wellness file uploaded: {wellness_file_id}")

        except Exception as e:
            logger.error(f"⚠️ Failed to initialize wellness service: {str(e)}")
            wellness_service = None
    else:
        if not anthropic_key:
            logger.warning("⚠️ ANTHROPIC_API_KEY not set - wellness features disabled")
        if not wellness_file_path:
            logger.warning("⚠️ WELLNESS_FILE_PATH not set - wellness features disabled")

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # Set up post-init callback for wellness service
    application.post_init = post_init

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setup", setup))
    application.add_handler(CommandHandler("schedule_meeting", schedule_meeting))
    application.add_handler(CommandHandler("wellness_info", wellness_info))
    application.add_handler(CommandHandler("wellness_reminders", wellness_reminders))
    application.add_handler(CommandHandler("wellness_create_new", wellness_create_new))
    application.add_handler(CommandHandler("help", help_command))

    logger.info("🚀 הבוט מתחיל בפולינג...")
    logger.info("מחכה להודעות...")

    # Run the bot with polling
    application.run_polling()

if __name__ == "__main__":
    main()
