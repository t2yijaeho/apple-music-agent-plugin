import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SCRIPTS = ROOT / "skills" / "apple-music-manager" / "scripts"


def run_script(name: str, *args: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


class OfflineHelperTests(unittest.TestCase):
    def test_library_planner_uses_isrc_and_marks_unmapped_candidate(self):
        report = run_script(
            "compare_library_snapshots.py",
            "--source", str(FIXTURES / "library-source.json"),
            "--target", str(FIXTURES / "library-target.json"),
            "--cache", str(FIXTURES / "id-map.json"),
        )
        self.assertEqual(report["matched_count"], 1)
        self.assertEqual(report["matched_by"], {"isrc": 1})
        self.assertEqual(report["proposed_adds"][0]["target_catalog_id"], "target-catalog-2")
        self.assertEqual(report["proposed_adds"][0]["status"], "candidate_add_review_required")

    def test_playlist_verifier_confirms_membership_and_order(self):
        report = run_script(
            "verify_playlist_snapshots.py",
            "--expected", str(FIXTURES / "playlist-expected.json"),
            "--actual", str(FIXTURES / "playlist-actual.json"),
        )
        self.assertTrue(report["complete"])
        self.assertTrue(report["membership_verified"])
        self.assertTrue(report["order_verified"])
        self.assertEqual(report["matched_count"], 2)


if __name__ == "__main__":
    unittest.main()
