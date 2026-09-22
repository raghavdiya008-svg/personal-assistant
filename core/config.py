"""
Configuration manager for Project JARVIS.
Handles environment variables, default settings, and service connections.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
VECTOR_DIR = DATA_DIR / "vector_store"
AUDIO_DIR = DATA_DIR / "audio_cache"

# Ensure data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables
load_dotenv(BASE_DIR / ".env")


class Config:
    """Global system configuration."""

    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR
    VECTOR_DIR: Path = VECTOR_DIR
    AUDIO_DIR: Path = AUDIO_DIR

    # Free Model Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "")
    HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", "")

    # Verified Working Frontier Models
    FAST_MODEL: str = "qwen/qwen3.8-27b"              # Groq high-speed (27B params, 500+ tok/s)
    REASONING_MODEL: str = "qwen/qwen3.8-27b"         # Groq deep reasoning & strategy
    MULTIMODAL_MODEL: str = "gemini-3.6-flash"        # Google AI Studio frontier multimodal/vision (1M context)

    # Telegram Cockpit
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")


    # Google Workspace / OAuth
    GOOGLE_OAUTH_CLIENT_SECRETS_FILE: str = os.getenv(
        "GOOGLE_OAUTH_CLIENT_SECRETS_FILE", str(BASE_DIR / "credentials.json")
    )
    GOOGLE_TOKEN_FILE: str = str(DATA_DIR / "token.json")

    # Payment & Invoicing
    STRIPE_API_KEY: str = os.getenv("STRIPE_API_KEY", "")

    # Voice / Speech Settings
    BOT_NAME: str = os.getenv("BOT_NAME", "JARVIS")
    VOICE_NAME: str = os.getenv("VOICE_NAME", "en-US-ChristopherNeural")

    # Database
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'jarvis.db'}"

    # Latency & Meeting Safety
    SPEECH_TIMEOUT_SECONDS: float = 3.0
    MEETING_AUTO_JOIN_LEAD_MINUTES: int = 2
    MAX_MEETING_DURATION_MINUTES: int = 45


settings = Config()

