"""
Autonomous Scheduler Agent for Project JARVIS.
Handles calendar negotiation, Google Meet room provisioning, and invite delivery.
"""

import datetime
import logging
from typing import Dict, Any, Optional
from core.memory import get_db_session, Lead, CallRecord
from core.state import event_bus, EVENT_MEETING_SCHEDULED, EVENT_TELEGRAM_NOTIFY
from tools.gcal_tool import calendar_tool
from tools.gmail_tool import gmail_tool

logger = logging.getLogger("JARVIS.Agent.Scheduler")


class SchedulerAgent:
    """Manages autonomous booking and Google Meet dispatch."""

    def __init__(self):
        event_bus.subscribe(EVENT_MEETING_SCHEDULED, self.on_schedule_request)

    def _parse_preferred_time(self, preferred_time_str: Optional[str]) -> Optional[datetime.datetime]:
        """Attempt to parse ISO or standard date/time strings if specified by client."""
        if not preferred_time_str or preferred_time_str.lower() in ("null", "none", "not specified"):
            return None
        # Try common datetime formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.datetime.strptime(preferred_time_str.strip(), fmt)
                if dt > datetime.datetime.utcnow():
                    return dt
            except ValueError:
                continue
        return None

    async def on_schedule_request(self, data: Dict[str, Any]):
        """Schedule a meeting slot and create Google Meet link."""
        lead_id = data.get("lead_id")
        email = data.get("email")
        name = data.get("name", "Client")
        preferred_time_raw = data.get("preferred_time")

        # 1. Determine target date and check availability
        preferred_dt = self._parse_preferred_time(preferred_time_raw)
        target_date = (preferred_dt.date() if preferred_dt else (datetime.datetime.utcnow() + datetime.timedelta(days=1)).date())
        available_slots = await calendar_tool.check_availability(target_date)

        if preferred_dt:
            meeting_time = preferred_dt
            logger.info(f"Using client preferred meeting time: {meeting_time.isoformat()}")
        elif available_slots:
            # Pick first available slot on target date
            slot_hour, slot_minute = map(int, available_slots[0].split(":"))
            meeting_time = datetime.datetime(
                target_date.year, target_date.month, target_date.day,
                slot_hour, slot_minute
            )
            logger.info(f"Selected earliest available slot ({available_slots[0]}): {meeting_time.isoformat()}")
        else:
            meeting_time = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
            logger.info(f"Fallback meeting time: {meeting_time.isoformat()}")
        
        # 2. Create Google Calendar & Meet link
        meeting_data = await calendar_tool.schedule_meeting(
            lead_name=name,
            lead_email=email,
            start_time=meeting_time,
            duration_minutes=30
        )
        meet_url = meeting_data["meet_url"]

        # 3. Persist call record in SQLite with transactional rollback support
        with get_db_session() as db:
            call_record = CallRecord(
                lead_id=lead_id,
                scheduled_time=meeting_time,
                meet_url=meet_url,
                deal_outcome="SCHEDULED"
            )
            db.add(call_record)

        # 4. Send confirmation email to client
        email_body = f"""Hi {name},

Thanks for reaching out! I've reserved a discovery session for us.

📅 Date/Time: {meeting_time.strftime('%B %d, %Y at %I:%M %p UTC')}

📹 Google Meet Room: {meet_url}

Looking forward to speaking with you!

Best,
JARVIS (Autonomous Executive)
"""
        await gmail_tool.send_email(
            to_email=email,
            subject=f"Confirmed: Discovery Call & Demo ({meeting_time.strftime('%b %d')})",
            body=email_body
        )

        # Notify Founder via Telegram
        await event_bus.emit(EVENT_TELEGRAM_NOTIFY, {
            "message": f"📅 *New Meeting Booked!*\n• Client: {name} ({email})\n• Time: {meeting_time.strftime('%I:%M %p UTC')}\n• Meet: {meet_url}"
        })


scheduler_agent = SchedulerAgent()
