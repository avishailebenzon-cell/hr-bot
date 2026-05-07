"""
Wellness Plan RAG Service - File management and Claude Files API integration
"""
import logging
import base64
from datetime import datetime
from typing import Optional
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class WellnessService:
    """Handles wellness plan file management and Q&A via Claude Files API."""

    def __init__(self, api_key: str):
        """Initialize Anthropic client."""
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.file_cache = {}  # {filename: {"file_content": bytes, "uploaded_at": datetime}}
        self.file_content = None  # Store file as base64 for Q&A

    async def upload_file(self, file_path: str) -> str:
        """
        Load Excel file and store as base64 for Claude API.

        Args:
            file_path: Path to the Excel file (e.g., wellness_plan_2026.xlsx)

        Returns:
            file_id: Dummy file ID (we store file as base64 instead)
        """
        try:
            with open(file_path, "rb") as f:
                file_content = f.read()
                file_name = file_path.split("/")[-1]

                # Store file content as base64
                self.file_content = base64.standard_b64encode(file_content).decode("utf-8")

                self.file_cache[file_name] = {
                    "uploaded_at": datetime.now().isoformat(),
                    "path": file_path,
                    "size": len(file_content),
                }

                logger.info(f"✅ Loaded wellness file: {file_name} (Size: {len(file_content)} bytes)")
                return file_name  # Return filename as ID

        except FileNotFoundError:
            logger.error(f"❌ File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading file: {str(e)}")
            raise

    async def answer_question(
        self, question: str, file_id: str, context: str = ""
    ) -> str:
        """
        Answer a question about the wellness plan using file content.

        Args:
            question: User's question in Hebrew or English
            file_id: ID of the wellness file (unused, uses self.file_content)
            context: Optional context for the question

        Returns:
            Answer from Claude based on the wellness plan file
        """
        try:
            if not self.file_content:
                raise ValueError("Wellness file not loaded. Call upload_file first.")

            prompt = f"""אתה עוזר תכנון הרווחה של הרמן.

המשתמש שואל שאלה לגבי תוכנית הרווחה:

{question}

בנה תשובה קצרה, מדויקת והעזור בהתבסס על הקובץ שלהלן."""

            if context:
                prompt += f"\n\nהקשר נוסף: {context}"

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    "data": self.file_content,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )

            answer = response.content[0].text
            logger.info(f"✅ Q&A processed for: {question[:50]}...")
            return answer

        except Exception as e:
            logger.error(f"❌ Error answering question: {str(e)}")
            raise

    async def generate_new_plan(
        self, file_id: str, year: int, changes: str
    ) -> str:
        """
        Generate a new wellness plan for a given year with modifications.

        Args:
            file_id: ID of the wellness file template (unused, uses self.file_content)
            year: Target year for new plan
            changes: Requested changes (e.g., "add 50 NIS to each gift")

        Returns:
            Generated plan text with proposed changes
        """
        try:
            if not self.file_content:
                raise ValueError("Wellness file not loaded. Call upload_file first.")

            prompt = f"""אתה מעצב תוכניות רווחה.

בהתבסס על תוכנית הרווחה הקיימת בקובץ, צור תוכנית חדשה לשנת {year} עם השינויים הבאים:

{changes}

אנא ספק:
1. סה"כ תקציב משוער
2. רשימת פעילויות מוצעות עם תאריכים
3. הערות על השינויים מהתוכנית הקודמת

תן תשובה בעברית ובפורמט ברור וקל לקריאה."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    "data": self.file_content,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )

            plan = response.content[0].text
            logger.info(f"✅ Generated new plan for {year}")
            return plan

        except Exception as e:
            logger.error(f"❌ Error generating plan: {str(e)}")
            raise

    def get_cached_file_id(self, filename: str) -> Optional[str]:
        """Get cached file ID if available."""
        if filename in self.file_cache:
            return self.file_cache[filename]["file_id"]
        return None

    def list_cached_files(self) -> dict:
        """List all cached wellness files."""
        return self.file_cache
