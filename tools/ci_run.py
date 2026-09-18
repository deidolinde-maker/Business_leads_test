"""Use argv, never concatenate CI filter values into shell commands."""
import os
import subprocess
import sys

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
    elif mode == "live":
        # The inventory retains blocked/excluded items for onboarding. A production
        # launch runs only entries whose form, Samara contract and confirmation are ready.
        args.append("--active-only")
else:
    raise SystemExit("Unknown mode")
args += ["--basetemp=artifacts/pytest-tmp", "--junitxml=artifacts/results.xml", "--alluredir=allure-results"]
raise SystemExit(subprocess.call(args))
