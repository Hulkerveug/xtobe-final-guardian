# Xtobe Voice Engine

`modules/voice_engine.py` provides opt-in, local Piper TTS for an original
Xtobe persona. It does not use cloud services, download models, or impersonate
any real person.

Enable it in the local `.env`:

```dotenv
XTOBE_VOICE_REPLIES_ENABLED=1
XTOBE_PIPER_BIN=piper
XTOBE_PIPER_MODEL=C:/secure/xtobe/voices/original-xtobe-medium.onnx
```

The model must already exist locally. Synthesis is limited to 1,000 characters,
30 seconds, and 25 MiB. Output files are created with random names in the
system temporary directory and should be removed with `cleanup_audio()` after
dispatch.
