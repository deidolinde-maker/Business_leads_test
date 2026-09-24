"""Read-only DOM probe for the approved Place pilot URLs.

No fields are filled and submit controls are never clicked. Non-read-only
network requests are aborted while the page is inspected.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.async_api import async_playwright


READ_ONLY = {"GET", "HEAD", "OPTIONS"}


def clean_url(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", "", ""))


async def probe(browser, case: dict, timeout_ms: int) -> dict:
    context = await browser.new_context(service_workers="block")
    writes = []

    async def guard(route):
        if route.request.method in READ_ONLY:
            await route.continue_()
        else:
            writes.append({"method": route.request.method, "url": clean_url(route.request.url)})
            await route.abort("blockedbyclient")

    await context.route("**/*", guard)
    page = await context.new_page()
    try:
        response = await page.goto(case["entry_url"], wait_until="domcontentloaded", timeout=timeout_ms)
        await page.wait_for_timeout(1600)
        # Dismiss only non-submit overlays; this keeps the probe read-only.
        for selector in ["#noButton", "#yesButton", ".popup-select-region__button.city",
                         ".popup-select-region__content-wrapper .popup__close",
                         "#cookieButton", "#cookieAccept", ".cookie-btn", ".cookie-accept"]:
            item = page.locator(selector).first
            if await item.count() and await item.is_visible():
                try:
                    await item.click(force=True, timeout=1500)
                    await page.wait_for_timeout(300)
                except Exception:
                    pass
        snapshot = await page.evaluate(
            """() => {
              const visible = el => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
              const text = el => (el?.innerText || el?.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 160);
              const attrs = el => ({tag: el.tagName.toLowerCase(), id: el.id || null,
                cls: el.className && typeof el.className === 'string' ? el.className : null,
                name: el.getAttribute('name'), type: el.getAttribute('type'),
                value: el.getAttribute('value'), placeholder: el.getAttribute('placeholder'),
                text: text(el)});
              const forms = [...document.querySelectorAll('form, .autocomplete-address, [class*=address]')]
                .filter(visible).slice(0, 30).map(el => ({...attrs(el),
                  action: el.getAttribute('action'),
                  controls: [...el.querySelectorAll('input, select, textarea, button')]
                    .filter(visible).slice(0, 40).map(attrs)}));
              const candidates = [...document.querySelectorAll('a, button, input, select, [role=button], [data-value]')]
                .filter(visible).filter(el => /подключ|заяв|провер|бизнес|офис|квартир|адрес|город|самар/i.test(text(el) + ' ' + (el.getAttribute('class') || '') + ' ' + (el.getAttribute('name') || '') + ' ' + (el.getAttribute('value') || '') + ' ' + (el.getAttribute('data-value') || '')))
                .slice(0, 80).map(el => ({...attrs(el), href: el.getAttribute('href'), data_value: el.getAttribute('data-value')}));
              const cityLinks = [...document.querySelectorAll('a[href]')].filter(el => /самар/i.test(text(el)) || el.id === '36401')
                .slice(0, 20).map(el => ({...attrs(el), href: el.href}));
              return {forms, candidates, cityLinks, title: document.title, body_text: text(document.body)};
            }"""
        )
        return {"case_id": case["case_id"], "url": case["entry_url"],
                "status": response.status if response else None, "final_url": clean_url(page.url),
                "blocked_writes": writes, **snapshot}
    except Exception as exc:
        return {"case_id": case["case_id"], "url": case["entry_url"],
                "error": f"{type(exc).__name__}: {str(exc).splitlines()[0]}", "blocked_writes": writes}
    finally:
        await context.close()


async def main(args):
    payload = json.loads(args.case_file.read_text(encoding="utf-8"))
    executable = os.getenv("BUSINESS_CHROMIUM_EXECUTABLE")
    launch = {"executable_path": executable} if executable else {}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(**launch)
        try:
            results = await asyncio.gather(*(probe(browser, case, args.timeout_ms) for case in payload["cases"]))
        finally:
            await browser.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"mode": "read_only_dom_probe", "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(results), "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-ms", type=int, default=20_000)
    asyncio.run(main(parser.parse_args()))
