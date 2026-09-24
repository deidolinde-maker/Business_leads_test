"""Use argv, never concatenate CI filter values into shell commands."""
import os
import subprocess
import sys

args = [sys.executable, "-m", "pytest"]
environment = os.getenv("BIZ_ENV", "prod")
if environment not in {"stage", "prod"}:
    raise SystemExit("Set TARGET_ENV to stage/prod. City is fixed to Samara.")
args += ["tests/test_business_submission.py", "--env=" + environment, "--active-only"]
for option, variable in (("--provider", "BIZ_PROVIDER"), ("--case-id", "BIZ_CASE_ID"),
                         ("--flow-kind", "BIZ_FLOW_KIND"), ("--domain", "BIZ_DOMAIN"),
                         ("--data-file", "BIZ_DATA_FILE")):
    value = os.getenv(variable, "").strip()
    if value:
        args += [option + "=" + value]
case_file = os.getenv("BIZ_CASE_FILE", "config/business_cases.json").strip()
if case_file:
    args += ["--case-file=" + case_file]
args += ["--basetemp=artifacts/pytest-tmp", "--junitxml=artifacts/results.xml", "--alluredir=allure-results"]
raise SystemExit(subprocess.call(args))
