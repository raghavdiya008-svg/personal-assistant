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
```

### 5. Run Overnight Autonomous Simulation
```bash
python main.py
```

---

## 🔒 Security & Compliance Notice
- Project JARVIS enforces unsuppressable AI identity disclosures on live calls to comply with California Bot Disclosure Law and EU AI Act Art. 52.
- Call recording requires verbal consent.
- Personal credentials, databases, and temporary audio files are strictly gitignored.
