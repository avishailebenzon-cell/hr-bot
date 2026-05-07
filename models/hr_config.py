from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, JSON
from database import Base

class HRConfig(Base):
    """HR workflow configuration for a user"""

    __tablename__ = "hr_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)  # Telegram user ID

    # Settings
    timezone = Column(String, default="Asia/Jerusalem")
    outlook_email = Column(String, nullable=True)  # User's Outlook calendar email
    outlook_access_token = Column(String, nullable=True)  # Encrypted token (stored as-is for MVP)
    outlook_refresh_token = Column(String, nullable=True)  # For token refresh
    outlook_token_expiry = Column(DateTime, nullable=True)

    # Company structure
    company_sites = Column(JSON, default=[])  # List of site names: ["Ness Ziona", "Tel Aviv"]
    site_managers = Column(JSON, default={})  # Dict: {"Ness Ziona": "manager@company.com"}

    # Tracking reminders (to prevent duplicates)
    last_quarterly_reminder = Column(DateTime, nullable=True)
    last_monthly_reminder = Column(DateTime, nullable=True)
    last_gift_check = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
