# 🤖 Project JARVIS: Sovereign Autonomous Enterprise AI Swarm

> **Autonomous multi-agent enterprise automation engine with real-time Google Meet voice negotiation, CRM qualification, calendar booking, legal compliance gates, and founder Telegram command.**

---

## 🌟 Key Features

- **⚡ Multi-Tier Cognitive Cascade:**
  - **Fast Reflex & Reasoning:** Powered by Groq Cloud (`Qwen 2.5 27B` at 500+ tokens/sec).
  - **Multimodal Intelligence:** Powered by Google AI Studio (`Gemini 2.5/3.6 Flash` with 1M token context).
  - **Speech-to-Text (STT):** Real-time audio transcription via Groq Whisper (`whisper-large-v3`).
  - **Neural Voice Synthesis (TTS):** Edge Neural Text-to-Speech (`en-US-ChristopherNeural`).
  - **Local Offline Fallback:** Automatic tri-provider fallback to local Ollama.

- **📞 Autonomous Google Meet Operator:**
  - Headless Chromium agent joins Google Meet calls autonomously.
  - Mandatory statutory AI identity disclosure & verbal recording consent gate.
  - Queries local ChromaDB vector memory for business FAQs and live client dialogue.

- **🛡️ Security, Privacy & Sandboxing Shield:**
  - **Prompt Injection Defense:** Intercepts jailbreaks and adversarial instructions before reaching LLM inference.
  - **Owner Impersonation Defense:** Prevents callers from claiming administrative authority on calls.
  - **Outbound Data Scrubber:** Automatic redaction of API keys, local PC directory paths, credit cards, and PII.
  - **Filesystem Sandbox Jail:** Enforces file read/writes strictly within `data/`.
  - **Virtual Media Isolation:** Uses emulated fake media devices; zero access to physical monitors, webcam, or microphone.

- **💳 Financial Authorization Gate:**
  - Deals above `$500.00` require explicit 1-click founder approval on Telegram before Stripe payment links are dispatched.

- **📊 Inbound Lead & CRM Automation:**
  - Analyzes inbound emails, extracts structured JSON, qualifies prospects, and negotiates Google Calendar slots.

- **📱 Founder Executive Telegram Cockpit:**
  - Voice command processing, instant deal/meeting alerts, and daily morning executive audio briefing.

---

## 🏗️ Architecture

```
                                  ┌────────────────────────┐
                                  │   Inbound Prospect     │
                                  │  (Email / Discovery)   │
                                  └───────────┬────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             JARVIS AGENT SWARM                              │
│                                                                             │
│  ┌──────────────────┐   ┌──────────────────────┐   ┌─────────────────────┐  │
│  │    LeadAgent     │──▶│    SchedulerAgent    │──▶│  GoogleMeetOperator │  │
│  │ (LLM Qualifier)  │   │   (Calendar & Meet)  │   │  (Live Voice & STT) │  │
│  └──────────────────┘   └──────────────────────┘   └──────────┬──────────┘  │
│                                                               │             │
│                                                               ▼             │
│  ┌──────────────────┐   ┌──────────────────────┐   ┌─────────────────────┐  │
│  │ Telegram Cockpit │◀──│    Security Guard    │◀──│   Financial Gate    │  │
│  │ (Founder Alert)  │   │ (Jailbreak / Redact) │   │ (Threshold Guard)   │  │
│  └──────────────────┘   └──────────────────────┘   └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

### 1. Prerequisites
- Python 3.10+
- FFmpeg (optional, for video processing)
- Virtual Environment recommended

### 2. Installation
```bash
git clone https://github.com/raghavdiya008-svg/personal-assistant.git
cd personal-assistant

pip install -r requirements.txt
playwright install chromium
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and provide your API keys:
```bash
cp .env.example .env
```
Populate `.env` with:
- `GROQ_API_KEY` (Free tier from console.groq.com)
- `GEMINI_API_KEY` (Free tier from aistudio.google.com)
- `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID` (Optional founder cockpit)

### 4. Run Test Suite
```bash
python -m pytest tests/ -v
# 50/50 tests passing (100% pass rate)
```

### 5. Launch Modes

#### Mode A: Interactive Personal Assistant (CLI / Voice)
```bash
# Interactive terminal chat
python jarvis.py

# Voice mode with microphone input and neural speech output
python jarvis.py --voice
```

#### Mode B: Sovereign Cockpit Web Server
```bash
python server.py
# Open http://localhost:8000 in your browser
```

#### Mode C: Containerized Infrastructure
```bash
docker compose up -d postgres redis minio litellm n8n
```

---

## 🏛️ Project JARVIS v2 Open-Source Architecture Stack

All core frameworks and upstream repositories integrated into Project JARVIS v2:

| Component | Repository / Provider | Role in JARVIS v2 |
|---|---|---|
| **Primary Project** | [`raghavdiya008-svg/personal-assistant`](https://github.com/raghavdiya008-svg/personal-assistant) | Main autonomous system codebase |
| **Authoritative State** | [`postgres/postgres`](https://github.com/postgres/postgres) | Authoritative event store, Consent Ledger, cryptographic approval tickets, audit trail |
| **Task Queue & Message Broker** | [`redis/redis`](https://github.com/redis/redis) | High-speed message broker, BullMQ queues, rate limiting |
| **Zero-Trust Secrets Vault** | [`core/vault.py`](file:///c:/Users/dksha/Documents/antigravity/magical-borg/core/vault.py) | Dynamic credential injection at capability boundary; agents never hold raw keys |
| **Model Gateway** | [`BerriAI/litellm`](https://github.com/BerriAI/litellm) | Deterministic latency-budget routing (<5s reflex, <15s reasoning) |
| **Agent Memory** | [`letta-ai/letta`](https://github.com/letta-ai/letta) | Stateful semantic & episodic memory blocks |
| **Capability Bus (MCP)** | [`modelcontextprotocol/python-sdk`](https://github.com/modelcontextprotocol/python-sdk) | Policy-governed capability execution platform |
| **Workflow Engine** | [`n8n-io/n8n`](https://github.com/n8n-io/n8n) | Distributed task scheduling and asynchronous integrations |
| **Web Navigation** | [`browser-use/browser-use`](https://github.com/browser-use/browser-use) | Autonomous web research with domain white-listing; output tagged `UNTRUSTED_EXTERNAL` |
| **Semantic Desktop Engine** | [`openinterpreter/open-interpreter`](https://github.com/openinterpreter/open-interpreter) | Safe semantic desktop actions (`take_screenshot`, `create_folder`, `move_file`) |
| **Local Second Brain** | [`khoj-ai/khoj`](https://github.com/khoj-ai/khoj) | Offline indexing & RAG for personal files and notes without cloud leakage |
| **Compliant Telephony** | [`vapi-ai`](https://github.com/VapiAI) / [`retell-ai`](https://github.com/RetellAI) | Compliant outbound calling strictly gated by the Postgres Consent Ledger |
| **Free API Multiplexer** | [`xxy2026/freellmapi`](https://github.com/xxy2026/freellmapi) | Opportunistic burst compute pool across free LLM endpoints |
| **Sandbox Execution** | [`All-Hands-AI/OpenHands`](https://github.com/All-Hands-AI/OpenHands) | Ephemeral, isolated execution environment without host docker.sock |
| **Tool Quarantine Pipeline** | [`builderio/micro-agent`](https://github.com/builderio/micro-agent) | 6-stage tool promotion gate with AST static security scanner |
| **Observability & Tracing** | [`langfuse/langfuse`](https://github.com/langfuse/langfuse) | Distributed execution telemetry with outbound secret masking |
| **Prompt Optimization** | [`stanfordnlp/dspy`](https://github.com/stanfordnlp/dspy) | Offline evaluation and mathematical prompt optimization |
| **Object Storage** | [`minio/minio`](https://github.com/minio/minio) | S3-compatible immutable storage for screenshots, DOMs, and call audio |

---

## 🔒 Security & Compliance Notice
- **Zero-Trust Capability Boundary:** Agents propose intent; only capabilities cross security boundaries.
- **Cryptographic Approvals:** All sensitive actions (email dispatch, telephony, shell) require tamper-evident HMAC-SHA256 signed approval tickets.
- **Affirmative Consent Ledger:** Unsolicited commercial telephony or email is blocked at the policy layer.
- **Offline Private Data:** Personal files, tax documents, and private notes are indexed locally via the Second Brain engine and never sent to cloud models.
