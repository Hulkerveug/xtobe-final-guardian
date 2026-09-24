"""Tests for deterministic local routing."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from connector import worker


class WorkerRoutingTests(unittest.TestCase):
    def test_unknown_text_is_acknowledged_without_execution(self):
        reply = worker._route("please run an arbitrary shell command", None)
        self.assertIn("No matching local tool", reply)

    def test_cv_request_does_not_mutate_a_document(self):
        reply = worker._route("update my cv", None)
        self.assertIn("remains disabled", reply)

    @patch.object(worker, "PROJECT_ROOT", Path(tempfile.gettempdir()))
    def test_validated_file_is_stored_by_suffix(self):
        source = Path(tempfile.gettempdir()) / "xtobe-routing-test.csv"
        source.write_text("phone,name,service,source\n", encoding="utf-8")
        try:
            destination = worker._store_routed(source, "caller leads")
            self.assertEqual("caller_batches", destination.parent.name)
            self.assertTrue(destination.exists())
        finally:
            source.unlink(missing_ok=True)
            (Path(tempfile.gettempdir()) / "data" / "caller_batches" / source.name).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
