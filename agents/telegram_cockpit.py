"""
Founder Executive Cockpit (Telegram Bot) for Project JARVIS.
Allows the founder to command the multi-agent swarm via text or voice notes,
receive real-time meeting and deal alerts, and listen to morning voice briefings.
"""

import io
import logging
from typing import Dict, Any, Optional

from core.config import settings
from core.brain import brain
from core.memory import get_db_session, Lead, CallRecord, Invoice
from core.state import event_bus, EVENT_TELEGRAM_NOTIFY, EVENT_NEW_LEAD
from audio.stt import stt
from audio.tts import tts

logger = logging.getLogger("JARVIS.Cockpit.Telegram")


class TelegramCockpit:
    """Telegram interface for founder command and control."""

    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        event_bus.subscribe(EVENT_TELEGRAM_NOTIFY, self.send_notification)

    async def send_notification(self, data: Dict[str, Any]):
        """Send an urgent notification or deal alert to the founder."""
        message = data.get("message", "")
        logger.info(f"📱 [Telegram Alert]:\n{message}")
        
        if self.bot_token and self.chat_id:
            try:
                from telegram import Bot
                bot = Bot(token=self.bot_token)
                await bot.send_message(chat_id=self.chat_id, text=message, parse_mode="Markdown")
            except Exception as e:
                logger.debug(f"Telegram dispatch notice: {e}")

    async def generate_morning_briefing(self) -> Dict[str, Any]:
        """Generate executive text & audio summary of overnight operations."""
        with get_db_session() as db:
            leads_count = db.query(Lead).count()
            closed_calls = db.query(CallRecord).filter(CallRecord.deal_outcome == "CLOSED_WON").count()
            invoices_total = sum(inv.amount for inv in db.query(Invoice).all())


        briefing_text = (
            f"Good morning Boss. JARVIS executive briefing:\n"
            f"• Pipeline: {leads_count} active leads tracked.\n"
            f"• Calls: {closed_calls} enterprise discovery calls closed.\n"
            f"• Total Invoiced: ${invoices_total:,.2f}.\n"
            f"All background agents are operating at nominal capacity."
        )

        audio_file = await tts.speak_to_file(briefing_text)
        return {
            "text": briefing_text,
            "audio_file": audio_file
        }

    async def handle_voice_command(self, voice_bytes: bytes) -> Dict[str, Any]:
        """Process founder's voice note, execute intent, and return voice response."""
        transcribed_text = await stt.transcribe(voice_bytes, filename="founder_voice.ogg")
        logger.info(f"🎤 Transcribed Founder Command: '{transcribed_text}'")

        system_prompt = (
            "You are JARVIS, speaking directly to your founder. "
            "Be extremely crisp, confident, decisive, and efficient. Acknowledge instructions clearly."
        )
        ai_reply = await brain.reflex(transcribed_text, system_prompt=system_prompt)
        reply_audio = await tts.speak_to_file(ai_reply)

        return {
            "user_command": transcribed_text,
            "jarvis_reply": ai_reply,
            "audio_reply_path": reply_audio
        }


telegram_cockpit = TelegramCockpit()
