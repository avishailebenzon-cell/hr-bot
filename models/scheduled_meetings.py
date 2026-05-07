from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Enum as SQLEnum
from database import Base

class MeetingType(str, Enum):
    """Types of meetings that can be scheduled"""
    TEAM_LUNCH = "team_lunch"
    SITE_VISIT = "site_visit"
    COMPANY_EVENT = "company_event"
    CUSTOM = "custom"

class MeetingStatus(str, Enum):
    """Status of a scheduled meeting"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class ScheduledMeeting(Base):
    """A meeting scheduled via the HR bot"""

    __tablename__ = "scheduled_meetings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("hr_configs.id"), nullable=False, index=True)

    # Meeting details
    meeting_type = Column(SQLEnum(MeetingType), default=MeetingType.CUSTOM)
    event_name = Column(String, nullable=False)  # e.g., "Team Lunch - Ness Ziona"
    description = Column(String, nullable=True)

    # Scheduling
    scheduled_date = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, default=60)

    # Recipients
    recipients = Column(JSON, default=[])  # List of email addresses

    # Outlook integration
    outlook_event_id = Column(String, nullable=True, unique=True)  # From Microsoft Graph
    outlook_event_url = Column(String, nullable=True)

    # Status
    status = Column(SQLEnum(MeetingStatus), default=MeetingStatus.DRAFT)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
