"""Use argv, never concatenate CI filter values into shell commands."""
import os
import subprocess
import sys

mode = os.getenv("BIZ_MODE", "local")
args = [sys.executable, "-m", "pytest"]
if mode == "local":
    args += ["tests/unit", "tests/browser"]
elif mode in {"collect", "live"}:
    environment = os.getenv("BIZ_ENV")
    if environment not in {"stage", "prod"}:
        raise SystemExit("Set TARGET_ENV to stage/prod. City is fixed to Samara.")
    args += ["tests/test_business_submission.py", "--env=" + environment]
    for option, variable in (("--provider", "BIZ_PROVIDER"), ("--case-id", "BIZ_CASE_ID"), ("--data-file", "BIZ_DATA_FILE")):
        value = os.getenv(variable, "").strip()
        if value:
            args += [option + "=" + value]
    if mode == "collect":
        args.append("--collect-only")
else:
    raise SystemExit("Unknown mode")
args += ["--junitxml=artifacts/results.xml", "--alluredir=allure-results"]
raise SystemExit(subprocess.call(args))
