import sys
import io
import asyncio
import logging

# Ensure UTF-8 output encoding for Windows PowerShell/CMD
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import signal
from colorama import init, Fore, Style

from core.config import settings
from core.state import event_bus, EVENT_NEW_LEAD, EVENT_MEETING_SCHEDULED
from core.memory import vector_memory, get_db_session, Lead
from agents.lead_agent import lead_agent
from agents.scheduler_agent import scheduler_agent
from agents.meet_operator import meet_operator
from agents.media_agent import media_agent
from agents.telegram_cockpit import telegram_cockpit
from audio.tts import tts


init(autoreset=True)
logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("JARVIS.Master")


async def seed_knowledge_base():
    """Populate default business facts and objection playbooks into vector memory."""
    facts = [
        ("pricing_faq", "Our enterprise package is $1,500/month, which includes 24/7 autonomous agents, CRM integration, and video pipeline."),
        ("capabilities_faq", "JARVIS can autonomously answer client discovery calls on Google Meet, qualify leads, and generate invoices while you sleep."),
        ("tech_stack", "The architecture runs on a free-tier cognitive cascade combining fast 8B reflex models, 70B reasoning models, and local vector memory."),
    ]
    for doc_id, text in facts:
        vector_memory.add_knowledge(doc_id=doc_id, text=text)
    logger.info("Knowledge base seeded into local ChromaDB memory.")


async def run_end_to_end_simulation():
    """
    Run an end-to-end simulation of the overnight cycle:
    1. Simulate inbound lead email from an enterprise client.
    2. LeadAgent qualifies and enriches the lead.
    3. SchedulerAgent books Google Meet and sends invitation.
    4. MeetOperator launches Playwright bot, enters Google Meet, handles dialogue, and closes $1,500 deal.
    5. Invoices and follow-ups are sent, and a Telegram Morning Briefing is delivered.
    """
    print("\n====================================================================")
    print("      [+] PROJECT JARVIS: SOVEREIGN AUTONOMOUS ENTERPRISE ENGINE      ")
    print("====================================================================\n")

    # Clean up expired audio files from previous runs
    tts.cleanup_cache(max_age_hours=24)

    await seed_knowledge_base()

    # Step 1: Simulate Inbound Lead
    sample_lead = {
        "email": "sarah.connor@cyberdyne-defense.com",
        "name": "Sarah Connor",
        "content": "Hi, we are scaling our defense software pipeline and need an automated agent system to handle client demos and inbound support. Budget is $15k/year. Can we meet today?"
    }
    logger.info(f"📥 Simulating Inbound Lead: {sample_lead['name']} ({sample_lead['email']})")
    await event_bus.emit(EVENT_NEW_LEAD, sample_lead)

    # Allow event loop to process qualification & scheduling
    await asyncio.sleep(2)

    # Step 2: Retrieve the newly created call record
    with get_db_session() as db:
        lead = db.query(Lead).filter(Lead.email == sample_lead["email"]).first()
        call_record = lead.calls[0] if lead and lead.calls else None
        meet_url = call_record.meet_url if call_record else "https://meet.google.com/abc-defg-hij"
        call_id = call_record.id if call_record else None

    # Step 3: Trigger the Google Meet Operator Bot
    logger.info(f"⏰ [2:58 AM Trigger] Auto-launching Google Meet Bot for: {meet_url}")
    await meet_operator.attend_meeting(meet_url=meet_url, call_record_id=call_id)


    # Step 4: Generate Morning Briefing
    logger.info("🌅 [08:00 AM Trigger] Generating Founder Morning Briefing...")
    briefing = await telegram_cockpit.generate_morning_briefing()
    print(f"\n{Fore.YELLOW}--------------------------------------------------------------------")
    print(f"📱 FOUNDER TELEGRAM AUDIO & TEXT BRIEFING:")
    print(f"--------------------------------------------------------------------{Style.RESET_ALL}")
    print(briefing["text"])
    if briefing["audio_file"]:
        print(f"🎙️ Audio Briefing File: {briefing['audio_file']}")
    print(f"{Fore.YELLOW}--------------------------------------------------------------------{Style.RESET_ALL}\n")


if __name__ == "__main__":
    asyncio.run(run_end_to_end_simulation())
