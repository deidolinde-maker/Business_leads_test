import json
from pathlib import Path
import subprocess
import sys

from tests.support import make_case


def run_cli(tmp_path, arguments):
    case = make_case()
    case.update(status="blocked", reason="Synthetic pending contract")
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"cases": [case]}), encoding="utf-8")
    return subprocess.run([sys.executable, "-m", "pytest", "tests/test_business_submission.py",
                           "--case-file=" + str(path), "--artifact-dir=" + str(tmp_path / "results"),
                           "-q", *arguments], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)


def test_blocked_case_fails_without_browser(tmp_path):
    result = run_cli(tmp_path, ["--env=stage"])
    assert result.returncode == 1, result.stdout + result.stderr
    summary = json.loads((tmp_path / "results/summary.json").read_text(encoding="utf-8"))
    assert summary["blocked"] == 1 and summary["complete"] is False
    assert "BLOCKED" in result.stdout


def test_collection_is_not_live_success(tmp_path):
    result = run_cli(tmp_path, ["--env=stage", "--collect-only"])
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads((tmp_path / "results/summary.json").read_text(encoding="utf-8"))
    assert summary["mode"] == "collection" and summary["complete"] is False


def test_missing_environment_is_usage_error(tmp_path):
    result = run_cli(tmp_path, [])
    assert result.returncode != 0
    assert "--env=stage or --env=prod is required" in result.stdout + result.stderr
