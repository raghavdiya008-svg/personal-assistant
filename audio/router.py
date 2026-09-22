"""
Audio Routing & Device Manager for Project JARVIS.

Handles virtual audio cable detection and redirection for browser automation.

IMPORTANT: A 24/7 production daemon should run on Linux. Both VB-Cable (Windows-only)
and Loopback (macOS-only) are DESKTOP tools and do NOT work on headless Linux servers.
For Linux production servers, use PulseAudio null-sink or PipeWire loopback module.
"""

import sys
import logging
from typing import Dict

logger = logging.getLogger("JARVIS.AudioRouter")


class AudioRouter:
    """Manages audio in/out virtual device paths for browser automation."""

    @staticmethod
    def get_recommended_devices() -> Dict[str, str]:
        """Detect and return correct virtual audio setup instructions for the current OS."""
        platform = sys.platform
        if platform.startswith("win"):
            # Windows local dev only — NOT suitable for 24/7 server deployment
            return {
                "input_device": "CABLE Output (VB-Audio Virtual Cable)",
                "output_device": "CABLE Input (VB-Audio Virtual Cable)",
                "notes": (
                    "Install VB-Cable from https://vb-audio.com/Cable/. "
                    "Windows is suitable for LOCAL DEV only. "
                    "For 24/7 production, deploy to Linux with PulseAudio."
                )
            }
        elif platform.startswith("darwin"):
            # macOS local dev only
            return {
                "input_device": "BlackHole 2ch",
                "output_device": "BlackHole 2ch",
                "notes": (
                    "Install via 'brew install blackhole-2ch'. "
                    "macOS is suitable for LOCAL DEV only."
                )
            }
        else:
            # Linux — CORRECT platform for 24/7 production daemon
            return {
                "input_device": "jarvis_sink.monitor",
                "output_device": "jarvis_sink",
                "notes": (
                    "Run these commands to set up PulseAudio virtual sink:\n"
                    "  pactl load-module module-null-sink sink_name=jarvis_sink sink_properties=device.description=JARVIS_Sink\n"
                    "  pactl load-module module-virtual-source source_name=jarvis_source master=jarvis_sink.monitor\n"
                    "For headless servers, start PulseAudio with: pulseaudio --start --daemonize\n"
                    "Then launch Chromium with: --use-fake-ui-for-media-stream"
                )
            }


audio_router = AudioRouter()
