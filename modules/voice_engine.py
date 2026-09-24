"""Offline Piper voice synthesis for original Xtobe personas."""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

VOICE_TRIGGERS = ("voice reply", "voice note", "speak", "as audio", "send as voice")


def should_use_voice(command_text: str) -> bool:
    """Enable voice only when explicitly requested or globally opted in."""
    enabled = os.getenv("XTOBE_VOICE_REPLIES_ENABLED", os.getenv("ENABLE_VOICE", "0")).lower() in {"1", "true", "yes"}
    return enabled or any(trigger in (command_text or "").lower() for trigger in VOICE_TRIGGERS)


class VoiceEngineError(RuntimeError):
    """Raised when local voice synthesis cannot be performed safely."""


class SecureVoiceEngine:
    """Synthesize bounded text with an explicitly configured local Piper model."""

    def __init__(self, enabled: Optional[bool] = None, model_path: Optional[str] = None, piper_binary: Optional[str] = None):
        self.enabled = os.getenv("XTOBE_VOICE_REPLIES_ENABLED", "0") == "1" if enabled is None else enabled
        self.model_path = model_path or os.getenv("XTOBE_PIPER_MODEL", "")
        self.piper_binary = piper_binary or os.getenv("XTOBE_PIPER_BIN", "piper")

    def validate_environment(self) -> Path:
        if not self.enabled:
            raise VoiceEngineError("voice replies are disabled")
        model = Path(self.model_path).expanduser()
        if model.suffix.lower() != ".onnx":
            raise VoiceEngineError("voice model must be a local .onnx file")
        try:
            resolved = model.resolve(strict=True)
        except OSError as error:
            raise VoiceEngineError("voice model does not exist") from error
        if not resolved.is_file():
            raise VoiceEngineError("voice model is not a regular file")
        return resolved

    def synthesize_to_wav(self, text_prompt: str) -> str:
        model = self.validate_environment()
        clean_text = text_prompt.strip()
        if not clean_text or len(clean_text) > 1000:
            raise VoiceEngineError("text prompt must contain 1 to 1000 characters")
        fd, output_name = tempfile.mkstemp(prefix="xtobe-voice-", suffix=".wav")
        os.close(fd)
        output = Path(output_name)
        try:
            result = subprocess.run(
                [self.piper_binary, "--model", str(model), "--output_file", str(output)],
                input=clean_text.encode("utf-8"), capture_output=True, timeout=30, check=False,
            )
            if result.returncode != 0:
                detail = result.stderr.decode("utf-8", errors="replace")[-200:]
                raise VoiceEngineError(f"local Piper synthesis failed: {detail}")
            if not output.is_file() or output.stat().st_size == 0:
                raise VoiceEngineError("Piper returned no audio")
            if output.stat().st_size > 25 * 1024 * 1024:
                raise VoiceEngineError("generated audio exceeds the size limit")
            return str(output)
        except (OSError, subprocess.TimeoutExpired) as error:
            output.unlink(missing_ok=True)
            raise VoiceEngineError("local Piper synthesis could not complete") from error
        except Exception:
            output.unlink(missing_ok=True)
            raise

    def cleanup_audio(self, file_path: str) -> None:
        if not file_path:
            return
        try:
            path = Path(file_path).resolve()
            temp_root = Path(tempfile.gettempdir()).resolve()
            if path.is_file() and path.parent == temp_root and path.name.startswith("xtobe-voice-") and path.suffix == ".wav":
                path.unlink(missing_ok=True)
        except OSError:
            pass
