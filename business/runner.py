import json
import shutil
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect

from business.adapters import FormAdapter
from business.cases import validate_case
from business.controls import assert_business, set_business
from business.deadline import Deadline
from business.errors import BusinessCheckError
from business.region import assert_samara, ensure_samara


SUCCESS_URL_MARKERS = ("/tilda/form1/submitted", "/thanks")


def _success_url_matches(url: str, confirmation: dict) -> bool:
    current = (url or "").lower()
    kind = confirmation.get("kind")
    value = str(confirmation.get("value", "")).lower()
    if kind == "url":
        return current.rstrip("/") == value.rstrip("/")
    if kind == "url_contains":
        return value in current
    return any(marker in current for marker in SUCCESS_URL_MARKERS)


def _submit_and_confirm(page, form, case, deadline):
    """Submit like Everyday_test: re-resolve the button and retry once."""
    confirmation = case["confirmation"]
    last_error = None
    for attempt in range(2):
        submit = form.locator(case["form"]["submit"]).first
        deadline.mark("submission.submit_control")
        try:
            expect(submit).to_be_visible(timeout=deadline.ms())
            expect(submit).to_be_enabled(timeout=deadline.ms())
            submit.scroll_into_view_if_needed(timeout=deadline.ms())
            deadline.mark("submission.click")
            submit.click(force=True, timeout=deadline.ms())
        except Exception as exc:
            last_error = exc
            # CF7/Tilda can replace the button while validating the address.
            submit = form.locator(case["form"]["submit"]).first
            expect(submit).to_be_visible(timeout=deadline.ms())
            expect(submit).to_be_enabled(timeout=deadline.ms())
            submit.click(force=True, timeout=deadline.ms())

        deadline.mark("submission.confirmation")
        end = time.monotonic() + min(25.0, deadline.ms() / 1000)
        while time.monotonic() < end:
            if _success_url_matches(page.url, confirmation):
                return {"kind": "url", "value": page.url}
            for opened in page.context.pages:
                if _success_url_matches(opened.url, confirmation):
                    return {"kind": "url", "value": opened.url}
            page.wait_for_timeout(300)
        if _success_url_matches(page.url, confirmation):
            return {"kind": "url", "value": page.url}
        if attempt == 0:
            page.wait_for_timeout(min(800, deadline.ms()))

    if confirmation.get("kind") == "locator":
        expect(page.locator(confirmation["value"])).to_be_visible(timeout=deadline.ms())
        return {"kind": "locator", "value": confirmation["value"]}
    raise BusinessCheckError("submission_confirmation_not_observed") from last_error


def _safe_url(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" if parsed.scheme else parsed.path


def _ui_state(page, form) -> dict:
    state = {"url": _safe_url(page.url), "invalid_controls": [], "form_state": []}
    if form is None:
        return state
    try:
        state["invalid_controls"] = form.locator(":invalid").evaluate_all(
            """controls => controls.slice(0, 10).map(control => ({
                id: control.id || null,
                name: control.name || null,
                type: control.type || control.tagName.toLowerCase()
            }))"""
        )
        known_states = {"sent", "invalid", "failed", "spam", "aborted", "submitting", "resetting"}
        state["form_state"] = [
            value for value in (form.get_attribute("class") or "").split() if value in known_states
        ]
    except Exception:
        pass
    return state


def _finish_video(page, context, output: Path, keep: bool) -> None:
    video = page.video
    try:
        context.close()
        if keep:
            video.save_as(str(output / "failure.webm"))
        else:
            video.delete()
    finally:
        shutil.rmtree(output / ".video", ignore_errors=True)


def run_case(browser, case: dict, data: dict, output: Path, budget: float = 75) -> dict:
    validate_case(case)
    if case["status"] != "active":
        raise BusinessCheckError(f"{case['status']}:{case['reason']}")
    if data.get("city") != "Самара" or data.get("environment") != case["environment"]:
        raise BusinessCheckError("data_city_or_environment_mismatch")
    output.mkdir(parents=True, exist_ok=True)
    deadline = Deadline(budget)
    adapter = FormAdapter()
    for stale in (output / "failure.png", output / "failure.webm"):
        stale.unlink(missing_ok=True)
    context = browser.new_context(
        viewport={"width": 1366, "height": 900},
        record_video_dir=str(output / ".video"),
        record_video_size={"width": 1366, "height": 900},
    )
    page = context.new_page()
    form = None
    result = {"case_id": case["case_id"], "environment": case["environment"],
              "region_mode": case["region"]["mode"], "target_city": "Самара", "status": "failed"}
    try:
        with deadline.phase("navigation"):
            deadline.mark("navigation.open_entry")
            response = page.goto(case["entry_url"], wait_until="domcontentloaded", timeout=deadline.ms())
            if response and response.status >= 400:
                raise BusinessCheckError("navigation_failed")
            expect(page).to_have_url(case.get("entry_final_url", case["entry_url"]), timeout=deadline.ms())
        with deadline.phase("form"):
            deadline.mark("form.open_target")
            form = adapter.open_form(page, case, deadline)
        with deadline.phase("region"):
            deadline.mark("region.select_samara")
            form = ensure_samara(page, form, case, adapter, deadline)
        with deadline.phase("fill"):
            deadline.mark("fill.business_control")
            set_business(form, case, deadline)
            deadline.mark("fill.fields")
            adapter.fill(form, case, data, deadline)
            deadline.mark("fill.final_business_check")
            assert_business(form, case, deadline)
            deadline.mark("fill.final_samara_check")
            result["city_observed"] = assert_samara(
                form,
                case["region"],
                deadline,
                allow_unrendered=case["region"]["mode"] == "popup_selection",
            )
        with deadline.phase("submission"):
            result["confirmation_observed"] = _submit_and_confirm(page, form, case, deadline)
        result["status"] = "passed"
        return result
    except Exception as exc:
        if isinstance(exc, BusinessCheckError):
            result["error"] = str(exc)
        else:
            failed_step = deadline.failed_step or deadline.current_step
            result["error"] = f"{failed_step}:{type(exc).__name__}"
        result["ui_after_error"] = _ui_state(page, form)
        try:
            # Mask all visible data controls; no trace/raw body exports by default.
            page.screenshot(path=str(output / "failure.png"), mask=page.locator("input, textarea").all())
        except Exception:
            pass
        raise BusinessCheckError(result["error"]) from None
    finally:
        result["phase_seconds"] = deadline.timings
        (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        _finish_video(page, context, output, keep=result["status"] == "failed")
