"""Batch read-only discovery for blocked business-option candidates.

The tool never fills a form or clicks a submit control. All non-read-only browser
requests are aborted before they leave the browser. Its JSON report is discovery
evidence only: a human still verifies the Samara route and submission contract
before a case may become active.
"""

import argparse
import asyncio
import json
import os
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parent.parent
READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}


def clean_url(value: str) -> str:
    """Keep an observable URL useful without retaining a query or fragment."""
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", "", ""))


def select_candidates(cases: list[dict], provider: str | None, case_ids: set[str], offset: int, limit: int) -> list[dict]:
    """Return one entry per source URL, retaining every inventory case ID."""
    grouped = defaultdict(list)
    for case in cases:
        if case.get("status") != "blocked" or case.get("flow_kind") != "business_option":
            continue
        if provider and case.get("provider") != provider:
            continue
        if case_ids and case.get("case_id") not in case_ids:
            continue
        source = case.get("entry_url") or case.get("source_page_url")
        if source and urlsplit(source).scheme in {"http", "https"}:
            grouped[clean_url(source)].append(case["case_id"])
    rows = [
        {"url": url, "case_ids": sorted(case_ids_for_url)}
        for url, case_ids_for_url in sorted(grouped.items())
    ]
    rows = rows[offset:]
    return rows[:limit] if limit else rows


def classify(snapshot: dict) -> str:
    """Classify a DOM snapshot without making a live-business conclusion."""
    city_ui = snapshot.get("city_ui") or {}
    has_city_ui = bool(city_ui.get("indicator")) and city_ui.get("search_present") and city_ui.get("samara_choice_present")
    if snapshot.get("business_controls") and has_city_ui:
        return "candidate: business control and city UI observed"
    if snapshot.get("business_controls"):
        return "review: business control observed; city UI not observed"
    return "skip: no business control observed"


def template_key(result: dict) -> str | None:
    """Group only DOM lookalikes for onboarding prioritisation, never for activation."""
    controls = result.get("business_controls") or []
    if not controls:
        return None
    host = urlsplit(result.get("final_url") or result["url"]).hostname or "unknown"
    shape = sorted([
        {
            "tag": control.get("tag"),
            "name": control.get("name"),
            "options": control.get("options", []),
            "form_class": control.get("form_class"),
        }
        for control in controls
    ], key=lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True))
    return host + ":" + json.dumps(shape, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


async def inspect_one(browser, candidate: dict, timeout_ms: int) -> dict:
    context = await browser.new_context(service_workers="block")
    blocked_writes = []

    async def guard(route):
        request = route.request
        if request.method in READ_ONLY_METHODS:
            await route.continue_()
        else:
            blocked_writes.append({"method": request.method, "url": clean_url(request.url)})
            await route.abort("blockedbyclient")

    await context.route("**/*", guard)
    page = await context.new_page()
    try:
        response = await page.goto(candidate["url"], wait_until="domcontentloaded", timeout=timeout_ms)
        await page.wait_for_timeout(750)
        snapshot = await page.evaluate(
            """() => {
              const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
              const text = el => el ? (el.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 120) : '';
              const label = el => {
                if (el.id) {
                  const explicit = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
                  if (explicit) return text(explicit);
                }
                return text(el.closest('label'));
              };
              const controls = [...document.querySelectorAll('select, input[type="checkbox"], input[type="radio"]')]
                .filter(visible)
                .map(el => ({
                  tag: el.tagName.toLowerCase(), type: el.type || null, name: el.name || null,
                  id: el.id || null, value: el.value || null, label: label(el),
                  form_action: el.form ? el.form.action.split('?')[0] : null,
                  form_class: el.form ? [...el.form.classList]
                    .filter(name => !['init', 'resetting', 'sent', 'invalid', 'failed', 'spam'].includes(name))
                    .sort().join(' ') || null : null,
                  options: el.tagName === 'SELECT' ? [...el.options].map(option => option.value) : [],
                }))
                .filter(control => /для бизнеса|бизнес|офис/i.test([control.value, control.label, ...control.options].filter(Boolean).join(' ')));
              const cityIndicator = document.querySelector('#autocomplete_city_name');
              const citySearch = document.querySelector('#city-input');
              const cityChoice = document.querySelector('a.region_item.region_link[id="36401"], a[id="36401"]');
              return {
                visible_forms: [...document.forms].filter(visible).length,
                business_controls: controls,
                city_ui: {
                indicator: cityIndicator && visible(cityIndicator)
                  ? {text: text(cityIndicator), ui_id: cityIndicator.dataset.item || null} : null,
                  search_present: !!citySearch,
                  samara_choice_present: !!cityChoice,
                },
              };
            }"""
        )
        result = {
            **candidate,
            "http_status": response.status if response else None,
            "final_url": clean_url(page.url),
            **snapshot,
            "blocked_write_count": len(blocked_writes),
        }
        result["recommendation"] = classify(result)
        result["template_key"] = template_key(result)
        return result
    except Exception as exc:  # Report a per-URL failure and continue batch discovery.
        return {
            **candidate,
            "error": f"{type(exc).__name__}: {str(exc).splitlines()[0]}",
            "blocked_write_count": len(blocked_writes),
            "recommendation": "retry: page inspection did not complete",
            "template_key": None,
        }
    finally:
        await context.close()


async def discover(candidates: list[dict], concurrency: int, timeout_ms: int) -> list[dict]:
    executable = os.getenv("BUSINESS_CHROMIUM_EXECUTABLE")
    launch = {"executable_path": executable} if executable else {}
    semaphore = asyncio.Semaphore(concurrency)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**launch)

        async def limited(candidate):
            async with semaphore:
                return await inspect_one(browser, candidate, timeout_ms)

        try:
            return await asyncio.gather(*(limited(candidate) for candidate in candidates))
        finally:
            await browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only batch discovery of business-option controls")
    parser.add_argument("--case-file", type=Path, default=ROOT / "config/business_cases.json")
    parser.add_argument("--provider")
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--offset", type=int, default=0, help="skip this many matching unique URLs")
    parser.add_argument("--limit", type=int, default=12, help="0 inspects every matching unique URL")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout-ms", type=int, default=20_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.offset < 0 or args.limit < 0 or args.concurrency < 1 or args.timeout_ms < 1:
        parser.error("offset and limit must be >= 0; concurrency and timeout-ms must be positive")

    cases = json.loads(args.case_file.read_text(encoding="utf-8"))["cases"]
    candidates = select_candidates(cases, args.provider, set(args.case_id), args.offset, args.limit)
    report = {
        "mode": "read_only_discovery",
        "safety": "All non-GET/HEAD/OPTIONS requests were aborted; no fields were filled and no submit was clicked.",
        "offset": args.offset,
        "selected_unique_urls": len(candidates),
        "results": asyncio.run(discover(candidates, args.concurrency, args.timeout_ms)) if candidates else [],
    }
    templates = defaultdict(list)
    for result in report["results"]:
        if result.get("template_key"):
            templates[result["template_key"]].append(result["url"])
    report["template_groups"] = [
        {"template_key": key, "url_count": len(urls), "representative_url": urls[0]}
        for key, urls in sorted(templates.items())
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"selected_unique_urls": len(candidates), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
