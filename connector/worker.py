"""Single-instance local worker; only deterministic echo is enabled."""
from __future__ import annotations

import hashlib
import os
import importlib.util
import time
from pathlib import Path
from typing import Optional

from connector import queue
from connector.guardian_commands import handle_whatsapp_message
from connector.dispatcher import DispatchError, download_media, send_text, send_whatsapp_voice, transcribe_audio
from modules.voice_engine import SecureVoiceEngine, VoiceEngineError, should_use_voice

DB_PATH = Path(os.environ.get("XTOBE_CONNECTOR_DB", queue.DEFAULT_DB))
POLL_SECONDS = max(0.5, float(os.environ.get("XTOBE_CONNECTOR_POLL_SECONDS", "2")))
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_crm_workflow():
    path = PROJECT_ROOT / "skills" / "crm_onboarding" / "crm_workflow.py"
    spec = importlib.util.spec_from_file_location("xtobe_crm_workflow", path)
    if not spec or not spec.loader:
        raise RuntimeError("CRM workflow is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _route(text: str, media_path: Optional[Path]) -> str:
    """Deterministically route authenticated content; never execute free text."""
    lowered = text.strip().lower()
    command = handle_whatsapp_message(text)
    if command["command"] != "unknown":
        return str(command["message"])
    if media_path and media_path.suffix.lower() in {".csv", ".json"}:
        results = _load_crm_workflow().process_caller_batch(str(media_path))
        return f"CRM ingested {len(results)} lead rows and queued {len(results)} local welcome messages."
    if any(term in lowered for term in ("edit cv", "update my cv", "resume", "mortgage metrics")):
        return "CV request recognized. The document tool is registered but remains disabled until a validated editor is installed."
    if any(term in lowered for term in ("crm", "caller", "lead sheet", "leads")):
        if media_path and media_path.suffix.lower() in {".csv", ".json"}:
            return "CRM request recognized."
        return "CRM request recognized. Send a CSV or JSON file with phone, name, service, and source columns."
    return "Message received. No matching local tool is enabled."


def _store_routed(media_path: Path, text: str) -> Path:
    """Move a validated download into a deterministic local intake folder."""
    lowered = text.lower()
    suffix = media_path.suffix.lower()
    if suffix in {".csv", ".json"}:
        folder = "caller_batches"
    elif suffix in {".pdf", ".docx"} or any(term in lowered for term in ("cv", "resume")):
        folder = "cv_uploads"
    else:
        folder = "inbox"
    destination = PROJECT_ROOT / "data" / folder / media_path.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(media_path, destination)
    return destination


def _reply(sender: str, text: str, trigger_text: str = "") -> None:
    if should_use_voice(trigger_text or text):
        audio = None
        try:
            audio = SecureVoiceEngine().synthesize_to_wav(text)
            send_whatsapp_voice(sender, audio)
            return
        except (VoiceEngineError, DispatchError, OSError):
            pass
        finally:
            if audio:
                SecureVoiceEngine().cleanup_audio(audio)
    send_text(sender, text)


def process_one(path: Path = DB_PATH) -> Optional[str]:
    message = queue.claim_one(path)
    if message is None:
        return None
    try:
        if message["media_id"]:
            digest = hashlib.sha256(message["media_id"].encode()).hexdigest()[:24]
            extension = {"audio/ogg": ".ogg", "audio/mpeg": ".mp3", "audio/mp4": ".m4a",
                         "audio/amr": ".amr", "audio/aac": ".aac", "application/pdf": ".pdf",
                         "text/plain": ".txt", "text/csv": ".csv", "application/json": ".json",
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                         "image/jpeg": ".jpg",
                         "image/png": ".png", "image/webp": ".webp"}[message["media_mime"]]
            media_path = Path(__file__).resolve().parent.parent / "data" / "incoming_media" / f"{digest}{extension}"
            download_media(message["media_id"], message["media_mime"], media_path)
            if message["media_mime"].startswith("audio/"):
                transcript = transcribe_audio(media_path)
                _reply(message["sender"], f"Voice note transcribed locally: {transcript}", transcript)
                _reply(message["sender"], _route(transcript, None), transcript)
            else:
                media_path = _store_routed(media_path, message["body"])
                _reply(message["sender"], _route(message["body"], media_path), message["body"])
        elif message["body"].strip().lower() == "echo":
            _reply(message["sender"], "Xtobe home node received your message.", message["body"])
        else:
            _reply(message["sender"], _route(message["body"], None), message["body"])
        queue.complete(message["message_id"], path)
        return message["message_id"]
    except DispatchError as error:
        queue.fail(message["message_id"], "dispatch_failed", path)
        print(f"Dispatch failed: {error}", flush=True)
    except Exception as error:
        queue.fail(message["message_id"], type(error).__name__[:32], path)
        print(f"Worker failed for message {message['message_id']}", flush=True)
    return None


def run_forever(path: Path = DB_PATH) -> None:
    while True:
        queue.requeue_expired(path)
        if process_one(path) is None:
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    run_forever()
