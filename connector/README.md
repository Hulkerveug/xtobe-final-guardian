# WhatsApp Home-Node Bridge

A local, webhook-first bridge for the Meta WhatsApp Cloud API. The HTTP
receiver and worker are separate single-purpose processes; no process is
spawned per webhook request.

## Security model

- Binds to `127.0.0.1:8000` by default. Put a private tunnel in front of it.
- Verifies `X-Hub-Signature-256` against the unmodified request body.
- Uses constant-time comparisons for both HMAC and webhook tokens.
- Requires an exact, comma-separated sender allowlist.
- Uses Meta message IDs as SQLite primary keys, making delivery retries safe.
- Stores message bodies locally and never writes them to application logs.
- Unknown commands are acknowledged but are not interpreted or executed.
- Document/CV tools are intentionally not registered in this first milestone.

## Configure

Add the values shown in `.env.example` to the repository's ignored `.env`:

- `WHATSAPP_APP_SECRET`: Meta App Secret
- `WHATSAPP_VERIFY_TOKEN`: independent random value configured in Meta
- `WHATSAPP_ALLOWED_SENDERS`: exact WhatsApp sender numbers
- `WHATSAPP_ACCESS_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID`: outbound Graph API

In Meta, configure the callback as
`https://YOUR_PRIVATE_TUNNEL/webhook/whatsapp` and subscribe only to the
`messages` webhook field.

## Start

```powershell
.\connector\run-connector.ps1
```

Only the first `echo` command has a deterministic local action. Text is
acknowledged but not interpreted. PDF, DOCX, CSV, JSON, plain text, JPEG, PNG, and WebP media up to 20 MiB
media up to 20 MiB are downloaded through authenticated Graph API metadata,
retained under `data\incoming_media`, and acknowledged. Voice notes are then
transcribed locally with `faster-whisper`; set `XTOBE_WHISPER_MODEL` to a model
name already present in the local Hugging Face/CTranslate2 cache. The worker
uses `local_files_only=True`, so transcription cannot silently download a model.

Install the optional local transcription dependency with:

```powershell
python -m pip install -r connector\requirements.txt
```

Validated CSV/JSON files are routed to `data\caller_batches` and processed by
the existing schema-validated CRM workflow. PDF/DOCX files are routed to
`data\cv_uploads`; CV mutation remains disabled until a deterministic editor is
validated. Other accepted media is retained under `data\inbox`. A voice
transcript uses the same router but cannot itself trigger a CV mutation.

Download the selected Whisper model once while online, then the bridge can
operate without model downloads. The durable inbox defaults to
`data\connector_queue.db`; override it with `XTOBE_CONNECTOR_DB`.

## Test

```powershell
python -m unittest discover -s connector -p 'test_*.py' -v
```
