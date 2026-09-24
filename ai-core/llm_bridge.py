"""
Xtobe Final Guardian - LLM Bridge
----------------------------------
Talks to a LOCAL Ollama server (no cloud). Requires:
    ollama serve            (usually auto-started by the Ollama installer)
    ollama pull llama3.1    (or mistral)

Usage:
    python llm_bridge.py --prompt "Xtobe, scan system"
    python llm_bridge.py --voice audio.wav   # transcribe with Whisper, then answer
"""
import argparse
import json
import os
import sys

MODEL = os.environ.get("XTOBE_MODEL", "llama3.1:8b")

SYSTEM_PROMPT = (
    "You are Xtobe, the Final Guardian AI running fully offline on the user's PC. "
    "You monitor processes, installers and network behavior, and can run suspicious "
    "software inside a QEMU sandbox. Answer briefly, technically, and proactively. "
    "If the user asks to scan or block something, describe the exact action you take."
)


def chat(prompt: str) -> str:
    try:
        import ollama
    except ImportError:
        return "ERROR: ollama python package missing. Run: pip install ollama"
    try:
        resp = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return resp["message"]["content"].strip()
    except Exception as e:
        return (
            f"ERROR: local LLM unreachable ({e}). "
            "Make sure Ollama is installed and `ollama pull llama3.1` has completed."
        )


def transcribe(wav_path: str) -> str:
    try:
        import whisper
    except ImportError:
        return ""
    model = whisper.load_model("base")
    return model.transcribe(wav_path)["text"].strip()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt")
    ap.add_argument("--voice", metavar="WAV")
    args = ap.parse_args()

    prompt = args.prompt
    if args.voice:
        text = transcribe(args.voice)
        if text:
            prompt = text

    if not prompt:
        print("ERROR: no prompt given")
        sys.exit(1)

    print(chat(prompt))
