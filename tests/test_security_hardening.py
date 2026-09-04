import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SecurityHardeningTests(unittest.TestCase):
    def test_public_instagram_status_never_contains_raw_log(self):
        payload = json.loads((ROOT / "data/instagram_publish_status.json").read_text(encoding="utf-8"))
        self.assertNotIn("log", payload)

    def test_instagram_workflow_suppresses_raw_api_output(self):
        workflow = (ROOT / ".github/workflows/instagram-daily.yml").read_text(encoding="utf-8")
        self.assertIn("> /tmp/instagram-publish.log 2>&1", workflow)
        self.assertNotIn("'log': log", workflow)

    def test_pr_workflows_do_not_give_write_token_to_validation(self):
        for name in (
            "serie-a-2026-update.yml",
            "serie-b-2026-update.yml",
            "libertadores-2026-update.yml",
            "copa-do-brasil-2026-update.yml",
        ):
            workflow = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
            self.assertIn("permissions:\n  contents: read", workflow, name)
            self.assertIn("validate-pr:", workflow, name)
            self.assertIn("persist-credentials: false", workflow, name)
            self.assertIn("update:", workflow, name)
            self.assertIn("contents: write", workflow, name)

    def test_dynamic_brasileirao_strings_are_escaped(self):
        script = (ROOT / "brasileirao.js").read_text(encoding="utf-8")
        self.assertIn("const safe = value =>", script)
        self.assertIn("${safe(row.name)}", script)
        self.assertIn("${safe(row.team)}", script)
        self.assertIn("${safe(team)}", script)

        shared = (ROOT / "site.js").read_text(encoding="utf-8")
        self.assertIn("const escapeHtml =", shared)
        self.assertIn("${escapeHtml(team)}", shared)


if __name__ == "__main__":
    unittest.main()
