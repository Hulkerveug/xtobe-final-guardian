"""Tests for the offline CRM onboarding skill."""
import csv
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent / "crm_workflow.py"
SPEC = importlib.util.spec_from_file_location("crm_workflow", MODULE_PATH)
assert SPEC and SPEC.loader
workflow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workflow)


class CrmWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "crm.db"
        workflow.initialize_database(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def write_csv(self, rows):
        path = self.root / "leads.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["phone", "name", "service", "source"])
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_duplicate_phone_is_upserted_not_duplicated(self):
        path = self.write_csv([
            {"phone": "+1 (555) 010-2000", "name": "One", "service": "advisory", "source": "web"},
            {"phone": "+15550102000", "name": "Two", "service": "support", "source": "web"},
        ])
        results = workflow.process_caller_batch(str(path), db_path=self.db)
        self.assertEqual(2, len(results))
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM leads").fetchone()[0])
            self.assertEqual("Two", connection.execute("SELECT name FROM leads").fetchone()[0])

    def test_json_ingestion_renders_expected_message(self):
        path = self.root / "leads.json"
        path.write_text(json.dumps([{
            "phone": "5550103000", "name": "Client", "service": "security", "source": "event"
        }]), encoding="utf-8")
        result = workflow.process_caller_batch(str(path), db_path=self.db)[0]
        self.assertTrue(result["message"].startswith("Hello Client, welcome!"))
        self.assertTrue(result["dispatch_ready"])

    def test_missing_phone_fails_deterministically(self):
        path = self.write_csv([
            {"phone": "", "name": "Nobody", "service": "advisory", "source": "web"}
        ])
        with self.assertRaisesRegex(workflow.WorkflowError, "invalid phone"):
            workflow.process_caller_batch(str(path), db_path=self.db)

    def test_unknown_template_placeholder_is_rejected(self):
        template = workflow.TEMPLATE_DIR / "bad.txt"
        template.write_text("Hello {{ secret }}", encoding="utf-8")
        try:
            path = self.write_csv([
                {"phone": "5550104000", "name": "A", "service": "B", "source": "C"}
            ])
            with self.assertRaisesRegex(workflow.WorkflowError, "unknown placeholders"):
                workflow.process_caller_batch(str(path), "bad", self.db)
        finally:
            template.unlink()

    def test_wrong_csv_columns_are_rejected(self):
        path = self.root / "bad.csv"
        path.write_text("phone,name\n5550105000,A\n", encoding="utf-8")
        with self.assertRaisesRegex(workflow.WorkflowError, "columns"):
            workflow.process_caller_batch(str(path), db_path=self.db)


if __name__ == "__main__":
    unittest.main()
