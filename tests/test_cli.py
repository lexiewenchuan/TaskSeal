import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CLITests(unittest.TestCase):
    def test_demo_runs_to_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(
                Path(__file__).resolve().parents[1] / "src"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "taskseal",
                    "--database",
                    str(root / "taskseal.db"),
                    "demo",
                    "--workspace",
                    str(root / "workspace"),
                ],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )

            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "accepted")
            self.assertEqual(payload["acceptance"][0]["status"], "passed")
            self.assertTrue((root / "workspace" / "taskseal-result.txt").is_file())


if __name__ == "__main__":
    unittest.main()
