"""Use argv, never concatenate CI filter values into shell commands."""
import os
import subprocess
import sys
import json
from pathlib import Path


def representative_case_ids() -> set[str]:
    path = Path(__file__).resolve().parents[1] / "config" / "representatives.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    case_ids = payload.get("case_ids")
    if not isinstance(case_ids, list) or not all(isinstance(case_id, str) and case_id for case_id in case_ids):
        raise SystemExit("representative case configuration is invalid")
    return set(case_ids)

mode = os.getenv("BIZ_MODE", "local")
args = [sys.executable, "-m", "pytest"]
if mode == "local":
    args += ["tests/unit", "tests/browser"]
elif mode in {"collect", "live", "representative"}:
    environment = os.getenv("BIZ_ENV")
    if environment not in {"stage", "prod"}:
        raise SystemExit("Set TARGET_ENV to stage/prod. City is fixed to Samara.")
    provider = os.getenv("BIZ_PROVIDER", "").strip()
    case_id = os.getenv("BIZ_CASE_ID", "").strip()
    if mode == "live" and (provider or not case_id):
        raise SystemExit("live mode requires one exact CASE_ID and an empty PROVIDER; use representative for the safe CI check.")
    if mode == "live" and case_id not in representative_case_ids():
        raise SystemExit("live mode accepts only a reviewed representative CASE_ID")
    test_path = "tests/test_representative_preflight.py" if mode == "representative" else "tests/test_business_submission.py"
    args += [test_path, "--env=" + environment]
    for option, variable in (("--provider", "BIZ_PROVIDER"), ("--case-id", "BIZ_CASE_ID"), ("--data-file", "BIZ_DATA_FILE")):
        value = os.getenv(variable, "").strip()
        if value:
            args += [option + "=" + value]
    if mode == "representative":
        if provider or case_id:
            raise SystemExit("representative mode does not accept PROVIDER or CASE_ID filters")
        args.append("--representatives")
    elif mode == "collect":
        args.append("--collect-only")
else:
    raise SystemExit("Unknown mode")
args += ["--basetemp=artifacts/pytest-tmp", "--junitxml=artifacts/results.xml", "--alluredir=allure-results"]
raise SystemExit(subprocess.call(args))
