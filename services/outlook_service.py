import logging
from datetime import datetime, timedelta
from typing import Optional, List
import httpx
from config import get_settings
from models import HRConfig

logger = logging.getLogger(__name__)
settings = get_settings()

class OutlookService:
    """Manages Outlook calendar operations via Microsoft Graph API"""

    def __init__(self):
        self.graph_url = settings.outlook_graph_url
        self.timeout = httpx.Timeout(30.0)

    async def create_meeting(
        self,
        user_config: HRConfig,
        title: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        recipients: Optional[List[str]] = None,
        description: str = "",
    ) -> Optional[str]:
        """
        Create a meeting in Outlook calendar.
        Returns: event_id from Microsoft Graph
        """
        if not user_config.outlook_access_token:
            logger.warning(f"User {user_config.user_id} has no Outlook token")
            return None

        if end_time is None:
            end_time = start_time + timedelta(hours=1)

        if recipients is None:
            recipients = []

        # Prepare attendees list
        attendees = [
            {"emailAddress": {"address": email, "name": email.split("@")[0]}}
            for email in recipients
        ]

        payload = {
            "subject": title,
            "body": {"contentType": "HTML", "content": description or title},
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": user_config.timezone,
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": user_config.timezone,
            },
            "attendees": attendees,
            "isReminderOn": True,
            "reminderMinutesBeforeStart": 15,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.graph_url}/me/events",
                    headers=self._get_auth_headers(user_config.outlook_access_token),
                    json=payload,
                )

                if response.status_code in [200, 201]:
                    event = response.json()
                    logger.info(
                        f"Created meeting '{title}' for user {user_config.user_id}: {event.get('id')}"
                    )
                    return event.get("id")
                else:
                    logger.error(
                        f"Failed to create meeting: {response.status_code} {response.text}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error creating meeting: {e}")
            return None

    async def get_user_info(self, access_token: str) -> Optional[dict]:
        """Get user email and other info from Outlook"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.graph_url}/me",
                    headers=self._get_auth_headers(access_token),
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get user info: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None

    async def refresh_token(self, refresh_token: str) -> Optional[dict]:
        """Refresh Outlook access token"""
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.outlook_client_id,
            "client_secret": settings.outlook_client_secret,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"https://login.microsoftonline.com/{settings.outlook_tenant_id}/oauth2/v2.0/token",
                    data=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Token refreshed successfully")
                    return data
                else:
                    logger.error(f"Failed to refresh token: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None

    @staticmethod
    def _get_auth_headers(access_token: str) -> dict:
        """Get Authorization headers for Graph API calls"""
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def get_oauth_url(state: str) -> str:
        """Get Microsoft OAuth authorization URL"""
        return (
            f"https://login.microsoftonline.com/{settings.outlook_tenant_id}/oauth2/v2.0/authorize?"
            f"client_id={settings.outlook_client_id}"
            f"&redirect_uri={settings.outlook_redirect_uri}"
            f"&response_type=code"
            f"&scope=Calendars.ReadWrite%20offline_access"
            f"&state={state}"
        )

    @staticmethod
    async def exchange_code_for_token(code: str) -> Optional[dict]:
        """Exchange authorization code for access token"""
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.outlook_client_id,
            "client_secret": settings.outlook_client_secret,
            "redirect_uri": settings.outlook_redirect_uri,
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                response = await client.post(
                    f"https://login.microsoftonline.com/{settings.outlook_tenant_id}/oauth2/v2.0/token",
                    data=payload,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to exchange code for token: {response.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            return None
