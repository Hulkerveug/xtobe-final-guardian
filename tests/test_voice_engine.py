"""Tests for the local-only Piper voice engine."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.voice_engine import SecureVoiceEngine, VoiceEngineError


class VoiceEngineTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with self.assertRaises(VoiceEngineError):
            SecureVoiceEngine(enabled=False).synthesize_to_wav("hello")

    def test_missing_model_is_rejected(self):
        engine = SecureVoiceEngine(enabled=True, model_path="missing.onnx", piper_binary="piper")
        with self.assertRaisesRegex(VoiceEngineError, "does not exist"):
            engine.synthesize_to_wav("hello")

    def test_successful_synthesis_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "original.onnx"
            model.write_bytes(b"model")
            def fake_run(command, **kwargs):
                Path(command[-1]).write_bytes(b"RIFFWAVE")
                return type("Result", (), {"returncode": 0, "stderr": b""})()
            with patch("modules.voice_engine.subprocess.run", side_effect=fake_run):
                path = SecureVoiceEngine(enabled=True, model_path=str(model), piper_binary="piper").synthesize_to_wav("hello")
            self.assertTrue(Path(path).exists())
            SecureVoiceEngine(enabled=True, model_path=str(model)).cleanup_audio(path)
            self.assertFalse(Path(path).exists())

    def test_empty_prompt_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "original.onnx"
            model.write_bytes(b"model")
            with self.assertRaises(VoiceEngineError):
                SecureVoiceEngine(enabled=True, model_path=str(model)).synthesize_to_wav("  ")


if __name__ == "__main__":
    unittest.main()
