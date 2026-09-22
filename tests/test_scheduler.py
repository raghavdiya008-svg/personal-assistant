"""Unit tests for SchedulerAgent and GoogleCalendarTool."""

import pytest
import datetime
from agents.scheduler_agent import SchedulerAgent
from tools.gcal_tool import GoogleCalendarTool


def test_scheduler_parse_preferred_time():
    scheduler = SchedulerAgent()

    # Valid future time
    future_dt = datetime.datetime.utcnow() + datetime.timedelta(days=2)
    time_str = future_dt.strftime("%Y-%m-%d %H:%M:%S")
    parsed = scheduler._parse_preferred_time(time_str)
    assert parsed is not None
    assert parsed.year == future_dt.year
    assert parsed.month == future_dt.month
    assert parsed.day == future_dt.day

    # Past time (should be rejected/return None)
    past_str = "2020-01-01 10:00:00"
    assert scheduler._parse_preferred_time(past_str) is None

    # None / garbage input
    assert scheduler._parse_preferred_time(None) is None
    assert scheduler._parse_preferred_time("invalid text string") is None


@pytest.mark.asyncio
async def test_gcal_tool_availability_and_booking():
    gcal = GoogleCalendarTool()
    slots = await gcal.check_availability(datetime.date.today())
    assert isinstance(slots, list)
    assert len(slots) > 0

    # Book a meeting
    meeting = await gcal.schedule_meeting(
        lead_name="John Doe",
        lead_email="john@example.com",
        start_time=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        duration_minutes=30
    )
    assert "meet.google.com" in meeting["meet_url"]
    assert meeting["status"] == "CONFIRMED"
