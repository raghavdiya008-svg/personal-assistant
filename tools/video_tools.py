"""
Video Processing Tool for Project JARVIS.
Uses FFmpeg to crop, zoom, and burn animated subtitles onto short-form video clips.
"""

import shutil
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("JARVIS.Tools.Video")


class VideoTool:
    """Automates video cutting and subtitle rendering via FFmpeg."""

    def __init__(self):
        self.ffmpeg_installed = shutil.which("ffmpeg") is not None

    def clip_video(
        self,
        input_path: str,
        output_path: str,
        start_seconds: float,
        end_seconds: float,
        vertical_crop: bool = True
    ) -> bool:
        """Cut a clip from a video and optionally convert to 9:16 vertical."""
        if not self.ffmpeg_installed:
            logger.warning("FFmpeg executable not found in PATH.")
            return False

        duration = end_seconds - start_seconds
        filter_str = "crop=ih*(9/16):ih" if vertical_crop else "null"

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(start_seconds),
            "-i", input_path,
            "-t", str(duration),
            "-vf", filter_str,
            "-c:v", "libx264",
            "-c:a", "aac",
            output_path
        ]

        try:
            logger.info(f"Rendering video clip: {input_path} -> {output_path}")
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr.decode('utf-8', errors='ignore')}")
            return False

    def extract_audio(self, video_path: str, output_audio_path: str) -> bool:
        """Extract audio from video as 16kHz mono WAV for Whisper STT."""
        if not self.ffmpeg_installed:
            logger.warning("FFmpeg executable not found in PATH.")
            return False

        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            output_audio_path
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except Exception as e:
            logger.error(f"Audio extraction error: {e}")
            return False


video_tool = VideoTool()

