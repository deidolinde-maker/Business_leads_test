import json
from pathlib import Path

from playwright.sync_api import expect

from business.adapters import FormAdapter
from business.cases import validate_case
from business.controls import assert_business, set_business
from business.deadline import Deadline
from business.errors import BusinessCheckError
from business.region import assert_samara, ensure_samara
from business.submission import SubmissionGuard


def run_case(browser, case: dict, data: dict, output: Path, budget: float = 75) -> dict:
    validate_case(case)
    if case["status"] != "active":
        raise BusinessCheckError(f"{case['status']}:{case['reason']}")
    if data.get("city") != "Самара" or data.get("environment") != case["environment"]:
        raise BusinessCheckError("data_city_or_environment_mismatch")
    output.mkdir(parents=True, exist_ok=True)
    deadline = Deadline(budget)
    adapter = FormAdapter()
    guard = SubmissionGuard(case["submission"], deadline)
    context = browser.new_context(service_workers="block", viewport={"width": 1366, "height": 900})
    page = context.new_page()
    result = {"case_id": case["case_id"], "environment": case["environment"],
              "region_mode": case["region"]["mode"], "target_city": "Самара", "status": "failed"}
    try:
        guard.install(context)
        with deadline.phase("navigation"):
            response = page.goto(case["entry_url"], wait_until="domcontentloaded", timeout=deadline.ms())
            if response and response.status >= 400:
                raise BusinessCheckError("navigation_failed")
            expect(page).to_have_url(case.get("entry_final_url", case["entry_url"]), timeout=deadline.ms())
        with deadline.phase("form"):
            form = adapter.open_form(page, case, deadline)
        with deadline.phase("region"):
            form = ensure_samara(page, form, case, adapter, deadline)
        with deadline.phase("fill"):
            set_business(form, case, deadline)
            adapter.fill(form, case, data, deadline)
            assert_business(form, case, deadline)
            result["city_observed"] = assert_samara(form, case["region"], deadline)
        with deadline.phase("submission"):
            guard.arm()
            submit = form.locator(case["form"]["submit"])
            expect(submit).to_have_count(1, timeout=deadline.ms())
            submit.click(timeout=deadline.ms())
            confirmation = case["confirmation"]
            if confirmation["kind"] == "url":
                expect(page).to_have_url(confirmation["value"], timeout=deadline.ms())
            else:
                expect(page.locator(confirmation["value"])).to_be_visible(timeout=deadline.ms())
            guard.assert_success()
        result["status"] = "passed"
        return result
    except Exception as exc:
        result["error"] = guard.error or (str(exc) if isinstance(exc, BusinessCheckError) else type(exc).__name__)
        try:
            # Mask all visible data controls; no trace/raw body exports by default.
            page.screenshot(path=str(output / "failure.png"), mask=page.locator("input, textarea").all())
        except Exception:
            pass
        raise BusinessCheckError(result["error"]) from None
    finally:
        result["phase_seconds"] = deadline.timings
        result["submission"] = {**guard.evidence, "observed": guard.seen, "forwarded": guard.forwarded,
                                "response_accepted": guard.accepted, "errors": guard.errors,
                                "background_blocked": guard.background_blocked}
        (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        context.close()
