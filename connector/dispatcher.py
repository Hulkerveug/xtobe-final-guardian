"""Minimal WhatsApp Graph API text dispatcher; credentials remain in env."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

GRAPH_VERSION = os.environ.get("WHATSAPP_GRAPH_VERSION", "v23.0")
API_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"


class DispatchError(RuntimeError):
    pass


def send_text(to: str, text: str) -> None:
    """Send a bounded text response. Raises on API or transport failure."""
    access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    if not access_token or not phone_number_id:
        raise DispatchError("WhatsApp Cloud API credentials are not configured")
    if not to or len(text) > 4096:
        raise DispatchError("invalid WhatsApp destination or message length")
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{API_URL}/{phone_number_id}/messages",
        data=payload,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status < 200 or response.status >= 300:
                raise DispatchError(f"Graph API returned HTTP {response.status}")
    except urllib.error.HTTPError as error:
        raise DispatchError(f"Graph API returned HTTP {error.code}") from error
    except urllib.error.URLError as error:
        raise DispatchError("Graph API is unreachable") from error



def send_whatsapp_voice(to: str, audio_path: str) -> None:
    """Upload a generated WAV to Graph, then send it as a WhatsApp audio message."""
    path = Path(audio_path).resolve()
    if not path.is_file() or path.suffix.lower() != ".wav" or path.stat().st_size > 16 * 1024 * 1024:
        raise DispatchError("voice payload must be a local WAV no larger than 16 MiB")
    token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
    phone_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    if not token or not phone_id:
        raise DispatchError("WhatsApp Cloud API credentials are not configured")
    boundary = "----XtobeVoiceBoundary7d3c"
    data = path.read_bytes()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"response.wav\"\r\n"
            "Content-Type: audio/wav\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"}
    upload = urllib.request.Request(f"{API_URL}/{phone_id}/media", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(upload, timeout=30) as response:
            media = json.loads(response.read(64 * 1024))
        media_id = media.get("id")
        if not isinstance(media_id, str) or not media_id:
            raise DispatchError("Graph API did not return a media ID")
        payload = json.dumps({"messaging_product": "whatsapp", "to": to, "type": "audio", "audio": {"id": media_id}}).encode()
        request = urllib.request.Request(f"{API_URL}/{phone_id}/messages", data=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status < 200 or response.status >= 300:
                raise DispatchError(f"Graph API returned HTTP {response.status}")
    except urllib.error.HTTPError as error:
        raise DispatchError(f"Graph API returned HTTP {error.code}") from error
    except urllib.error.URLError as error:
        raise DispatchError("Graph API is unreachable") from error


def download_media(media_id: str, mime_type: str, destination: Path) -> Path:
    """Resolve and download a Meta media ID with bounded streamed content."""
    from connector import queue
    access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
    if not access_token or mime_type not in queue.ALLOWED_MEDIA_MIME:
        raise DispatchError("media credentials or MIME type are not allowed")
    headers = {"Authorization": f"Bearer {access_token}"}
    total = 0
    completed = False
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{API_URL}/{media_id}", headers=headers), timeout=15) as response:
            metadata = json.loads(response.read(64 * 1024))
        download_url = metadata.get("url")
        if not isinstance(download_url, str) or not download_url.startswith("https://"):
            raise DispatchError("Graph API returned an invalid media URL")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(urllib.request.Request(download_url, headers=headers), timeout=30) as response, destination.open("wb") as output:
            while chunk := response.read(64 * 1024):
                total += len(chunk)
                if total > queue.MAX_MEDIA_BYTES:
                    raise DispatchError("media exceeds the 20 MiB limit")
                output.write(chunk)
        completed = True
        return destination
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise DispatchError("media download failed") from error
    finally:
        if not completed:
            destination.unlink(missing_ok=True)


def transcribe_audio(path: Path) -> str:
    """Transcribe with an already-installed/cached local Whisper model."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:
        raise DispatchError("faster-whisper is not installed") from error
    model = WhisperModel(os.environ.get("XTOBE_WHISPER_MODEL", "small"), device="cpu", compute_type="int8", local_files_only=True)
    segments, _ = model.transcribe(str(path), language="en", vad_filter=True, beam_size=5)
    text = " ".join(segment.text.strip() for segment in segments).strip()
    if len(text) > 4096:
        raise DispatchError("transcription exceeds the message limit")
    return text
