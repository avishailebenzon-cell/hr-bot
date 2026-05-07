from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Enum as SQLEnum
from database import Base

class ConversationStateType(str, Enum):
    """Types of HR conversations"""
    QUARTERLY_LUNCH = "quarterly_lunch"
    QUARTERLY_GIFTS = "quarterly_gifts"
    MONTHLY_SITE_VISIT = "monthly_site_visit"
    MONTHLY_COMPANY_EVENT = "monthly_company_event"
    CUSTOM_MEETING = "custom_meeting"

class ConversationState(Base):
    """Tracks multi-step conversations with users"""

    __tablename__ = "conversation_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("hr_configs.id"), nullable=False, index=True)

    # Conversation type
    state_type = Column(SQLEnum(ConversationStateType), nullable=False)

    # Current step in the flow (e.g., "awaiting_confirmation", "awaiting_date", "awaiting_recipients")
    current_step = Column(String, nullable=False)

    # Context data (persisted between messages)
    context_data = Column(JSON, default={})  # e.g., {"selected_sites": ["Ness Ziona"], "event_name": "Lunch"}

    # Expiry (conversations timeout after 24 hours)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
