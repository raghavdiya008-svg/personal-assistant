"""
FastAPI Server & Control Cockpit API for Project JARVIS v2.

Serves:
  1. Static UI Cockpit from ui/index.html on http://localhost:8000
  2. REST API for Live Chat routed through capability broker & trust taxonomy
  3. HITL Cryptographic Approval endpoints (list, approve, reject)
  4. Real-time Telemetry & System Status
"""

import time
import uvicorn
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.trust import TrustGuard, TrustLevel
from core.approvals import approval_engine, SecurityError
from core.capability_broker import capability_broker, ApprovalRequiredError
from core.gateway import llm_gateway
from core.security import SecurityGuard
from core.config import settings

# Ingest all capability modules to register with CapabilityBroker
import core.desktop
import core.second_brain
import core.telephony

app = FastAPI(title="JARVIS v2 Sovereign Cockpit API", version="2.0.0")

# Enable CORS for local cockpit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVER_START_TIME = time.time()
UI_DIR = settings.BASE_DIR / "ui"


# ── Request / Response Schemas ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    agent_id: str = "operator"
    approval_ticket_id: Optional[str] = None


class ApprovalActionRequest(BaseModel):
    operator_id: str = "human_operator"


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_ui():
    """Serve the primary Cockpit dashboard."""
    index_path = UI_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "JARVIS Sovereign Cockpit API v2 is running. UI file not found."}


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    Execute chat query through TrustGuard, Security filter, and LLM Gateway.
    """
    start_time = time.time()

    # 1. Security Guard: prompt injection & impersonation
    is_safe, threat_type, deflection = SecurityGuard.inspect_client_input(req.message)
    if not is_safe:
        return {
            "response": deflection or "Request deflected by security policy.",
            "trust_level": TrustLevel.OPERATOR_COMMAND.name,
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "threat_blocked": threat_type,
        }

    # 2. Tag with Operator Trust
    trusted_payload = TrustGuard.wrap_operator(req.message, source="web_cockpit")

    # 3. Model completion via Gateway
    try:
        raw_response = await llm_gateway.complete(
            prompt=trusted_payload.content,
            tier="reflex",
        )
        # 4. Outbound secret scrub
        sanitized = SecurityGuard.sanitize_outbound_text(raw_response)

        return {
            "response": sanitized,
            "trust_level": TrustLevel.MODEL_REASONING.name,
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "payload_id": trusted_payload.payload_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/approvals")
async def get_approvals():
    """List all pending cryptographic approval tickets."""
    return {
        "pending_tickets": approval_engine.get_pending_tickets(),
        "count": len(approval_engine.get_pending_tickets()),
    }


@app.post("/api/approvals/{ticket_id}/approve")
async def approve_ticket(ticket_id: str, req: ApprovalActionRequest):
    """Cryptographically sign and approve a ticket."""
    try:
        ticket = approval_engine.approve_ticket(ticket_id, operator_id=req.operator_id)
        return {"status": "SUCCESS", "ticket": ticket.to_dict()}
    except KeyError:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/approvals/{ticket_id}/reject")
async def reject_ticket(ticket_id: str, req: ApprovalActionRequest):
    """Reject an approval ticket."""
    try:
        ticket = approval_engine.reject_ticket(ticket_id, operator_id=req.operator_id)
        return {"status": "REJECTED", "ticket": ticket.to_dict()}
    except KeyError:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/capabilities")
async def list_capabilities():
    """List registered capabilities and risk boundary classifications."""
    return {
        name: {
            "risk_level": cap.risk_level.value,
            "requires_approval": cap.requires_approval,
            "allowed_agents": list(cap.allowed_agents),
            "rate_limit_per_min": cap.rate_limit_per_minute,
        }
        for name, cap in capability_broker._capabilities.items()
    }


@app.get("/api/telemetry")
async def get_telemetry():
    """System health, uptime, and security metrics."""
    uptime_sec = time.time() - SERVER_START_TIME
    return {
        "system": "Project JARVIS v2 Sovereign Operating Platform",
        "status": "OPERATIONAL",
        "uptime_seconds": round(uptime_sec, 1),
        "primary_model": settings.FAST_MODEL,
        "capabilities_registered": len(capability_broker._capabilities),
        "pending_approvals": len(approval_engine.get_pending_tickets()),
        "security_policy": "STRICT_CAPABILITY_BROKER",
    }


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
