"""
Inbound Lead & CRM Agent for Project JARVIS.
Autonomously processes incoming messages, scores lead qualification, and coordinates scheduling.
"""

import json
import logging
from typing import Dict, Any, Optional
from core.brain import brain
from core.memory import get_db_session, Lead
from core.state import event_bus, EVENT_NEW_LEAD, EVENT_MEETING_SCHEDULED


logger = logging.getLogger("JARVIS.Agent.Lead")


class LeadAgent:
    """Processes incoming leads and enriches CRM state."""

    def __init__(self):
        event_bus.subscribe(EVENT_NEW_LEAD, self.on_new_lead)

    async def on_new_lead(self, data: Dict[str, Any]):
        """Handler triggered when a new lead message is received."""
        email = data.get("email")
        content = data.get("content", "")
        sender_name = data.get("name", "Unknown")

        logger.info(f"🔍 LeadAgent analyzing inquiry from {email} ({sender_name})")
        qualification = await self.qualify_lead(email, sender_name, content)
        
        # Save or update in database
        with get_db_session() as db:
            lead = db.query(Lead).filter(Lead.email == email).first()
            if not lead:
                lead = Lead(
                    email=email,
                    name=qualification.get("name") or sender_name,
                    company=qualification.get("company", "Individual"),
                    status="QUALIFIED" if qualification.get("is_qualified") else "UNQUALIFIED",
                    notes=f"Budget: {qualification.get('budget')} | Needs: {qualification.get('summary')}"
                )
                db.add(lead)
            else:
                lead.status = "QUALIFIED" if qualification.get("is_qualified") else lead.status
                lead.notes = f"{lead.notes}\nUpdated Needs: {qualification.get('summary')}"

            db.flush()
            lead_id = lead.id

        if qualification.get("is_qualified"):

            logger.info(f"✨ Lead {email} is QUALIFIED! Triggering auto-scheduler.")
            await event_bus.emit(EVENT_MEETING_SCHEDULED, {
                "lead_id": lead_id,
                "email": email,
                "name": qualification.get("name") or sender_name,
                "company": qualification.get("company"),
                "preferred_time": qualification.get("preferred_time")
            })

    async def qualify_lead(self, email: str, name: str, message: str) -> Dict[str, Any]:
        """Use Fast Brain to parse lead details and qualification."""
        prompt = f"""
        Analyze this incoming client inquiry:
        From: {name} <{email}>
        Message: "{message}"

        Extract JSON with these keys:
        - "name": extracted name (or fallback)
        - "company": company name or "Unknown"
        - "budget": budget mentioned or "Not specified"
        - "is_qualified": boolean (true if serious business inquiry)
        - "preferred_time": any requested meeting date/time or null
        - "summary": 1-sentence summary of their request
        
        Return ONLY valid JSON.
        """
        response_text = await brain.reason(prompt, json_mode=True)
        try:
            # Strip markdown fences if LLM wraps JSON in ```json ... ```
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]  # remove first line
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
            return json.loads(cleaned)
        except Exception:
            logger.warning(f"Failed to parse LLM qualification response, using safe defaults (is_qualified=False)")
            return {
                "name": name,
                "company": "Unknown",
                "budget": "Not specified",
                "is_qualified": False,  # SAFE DEFAULT: don't auto-qualify on parse failure
                "preferred_time": None,
                "summary": message[:100]
            }


lead_agent = LeadAgent()
