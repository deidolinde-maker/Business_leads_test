import json
import os
from pathlib import Path

import pytest

from business.cases import ROOT, load_cases, load_data, select_cases
from business.errors import ConfigurationError


def pytest_addoption(parser):
    group = parser.getgroup("business-leads")
    group.addoption("--env", choices=["stage", "prod"])
    group.addoption("--provider")
    group.addoption("--case-id")
    group.addoption("--case-file", default=str(ROOT / "config/business_cases.json"))
    group.addoption("--data-file", default=str(ROOT / "config/data/samara.json"))
    group.addoption("--artifact-dir", default=str(ROOT / "artifacts"))


def pytest_generate_tests(metafunc):
    if "business_case" not in metafunc.fixturenames:
        return
    config = metafunc.config
    try:
        cases = select_cases(load_cases(Path(config.getoption("--case-file"))),
                             config.getoption("--env"), config.getoption("--provider"),
                             config.getoption("--case-id"))
    except (ConfigurationError, OSError, ValueError) as exc:
        raise pytest.UsageError(str(exc)) from exc
    config._business_cases = cases
    metafunc.parametrize("business_case", cases, ids=[c["case_id"] for c in cases])


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        options = {}
        if os.getenv("BUSINESS_CHROMIUM_EXECUTABLE"):
            options["executable_path"] = os.environ["BUSINESS_CHROMIUM_EXECUTABLE"]
        instance = playwright.chromium.launch(**options)
        yield instance
        instance.close()


@pytest.fixture
def live_data(request):
    return load_data(Path(request.config.getoption("--data-file")), request.config.getoption("--env"))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if "business_case" in getattr(item, "funcargs", {}):
        case = item.funcargs["business_case"]
        results = getattr(item.config, "_business_outcomes", {})
        if report.when == "call" or (report.when == "setup" and report.failed):
            results[case["case_id"]] = report.outcome
        if report.when == "teardown" and report.failed:
            results[case["case_id"]] = "failed"
        item.config._business_outcomes = results


def pytest_sessionfinish(session, exitstatus):
    config = session.config
    if not hasattr(config, "_business_cases"):
        return
    cases = config._business_cases
    outcomes = getattr(config, "_business_outcomes", {})
    summary = {"mode": "collection" if config.option.collectonly else "live",
               "selected": len(cases), "target_city": "Самара",
               "cases": [{"case_id": c["case_id"], "status": c["status"], "reason": c.get("reason"),
                          "outcome": outcomes.get(c["case_id"], "not_run")}
                         for c in cases]}
    for status in ("active", "blocked", "excluded"):
        summary[status] = sum(c["status"] == status for c in cases)
    summary["passed"] = sum(o == "passed" for o in outcomes.values())
    summary["failed"] = sum(o == "failed" for o in outcomes.values())
    summary["incomplete"] = sum(c["status"] == "active" and outcomes.get(c["case_id"]) not in {"passed", "failed"} for c in cases)
    summary["complete"] = (not config.option.collectonly and summary["active"] > 0
                           and not summary["blocked"] and not summary["failed"]
                           and not summary["incomplete"] and summary["passed"] == summary["active"])
    target = Path(config.getoption("--artifact-dir"))
    target.mkdir(parents=True, exist_ok=True)
    (target / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if not config.option.collectonly and not summary["complete"] and session.exitstatus == 0:
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter, config):
    if hasattr(config, "_business_cases"):
        terminalreporter.write_sep("=", "Business scope: Samara only")
        for case in config._business_cases:
            terminalreporter.write_line(f"{case['case_id']} [{case['status']}] {case.get('reason', '')}")
