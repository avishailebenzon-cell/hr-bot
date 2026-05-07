"""
Wellness Plan RAG Service - File management and Claude Files API integration
"""
import logging
from datetime import datetime
from typing import Optional
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class WellnessService:
    """Handles wellness plan file management and Q&A via Claude Files API."""

    def __init__(self, api_key: str):
        """Initialize Anthropic client."""
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-opus-4-1"
        self.file_cache = {}  # {filename: {"file_id": str, "uploaded_at": datetime}}

    async def upload_file(self, file_path: str) -> str:
        """
        Upload Excel file to Claude Files API.

        Args:
            file_path: Path to the Excel file (e.g., wellness_plan_2026.xlsx)

        Returns:
            file_id: Unique ID for the uploaded file in Claude's system
        """
        try:
            with open(file_path, "rb") as f:
                file_name = file_path.split("/")[-1]
                response = self.client.beta.files.upload(
                    file=(file_name, f.read()),
                )
                file_id = response.id

                self.file_cache[file_name] = {
                    "file_id": file_id,
                    "uploaded_at": datetime.now().isoformat(),
                    "path": file_path,
                }

                logger.info(f"✅ Uploaded wellness file: {file_name} (ID: {file_id})")
                return file_id

        except FileNotFoundError:
            logger.error(f"❌ File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"❌ Error uploading file: {str(e)}")
            raise

    async def answer_question(
        self, question: str, file_id: str, context: str = ""
    ) -> str:
        """
        Answer a question about the wellness plan using Claude Files API.

        Args:
            question: User's question in Hebrew or English
            file_id: ID of the uploaded wellness file
            context: Optional context for the question

        Returns:
            Answer from Claude based on the wellness plan file
        """
        try:
            prompt = f"""אתה עוזר תכנון הרווחה של הרמן.

המשתמש שואל שאלה לגבי תוכנית הרווחה:

{question}

בנה תשובה קצרה, מדויקת והעזור בהתבסס על הקובץ שלהלן."""

            if context:
                prompt += f"\n\nהקשר נוסף: {context}"

            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "file",
                                    "file_id": file_id,
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
            file_id: ID of the wellness file template
            year: Target year for new plan
            changes: Requested changes (e.g., "add 50 NIS to each gift")

        Returns:
            Generated plan text with proposed changes
        """
        try:
            prompt = f"""אתה מעצב תוכניות רווחה.

בהתבסס על תוכנית הרווחה הקיימת בקובץ, צור תוכנית חדשה לשנת {year} עם השינויים הבאים:

{changes}

אנא ספק:
1. סה"כ תקציב משוער
2. רשימת פעילויות מוצעות עם תאריכים
3. הערות על השינויים מהתוכנית הקודמת

תן תשובה בעברית ובפורמט ברור וקל לקריאה."""

            response = self.client.beta.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "file",
                                    "file_id": file_id,
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
