"""Read-only AST/text import. Never executes or imports either legacy test suite."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit


def assignments(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = (value, node.lineno)
    return found


def import_scope(everyday: Path, big: Path, shas: dict, output: Path):
    inventory = []
    locators = {"note": "Imported source candidates, not live-verified selectors.", "sources": {}}

    def add(repo, path, line, provider, url, flow, enabled, detail):
        inventory.append({"repo": repo, "sha": shas[repo], "path": path, "line": line,
                          "provider": provider, "url": url, "flow_kind": flow,
                          "source_enabled": enabled, "detail": detail,
                          "source_ref": f"https://github.com/deidolinde-maker/{repo}/blob/{shas[repo]}/{path}#L{line}"})

    for repo, directory, test_file in (("Everyday_test", everyday, "test_universal2.py"),
                                       ("Big_landing_test", big, "big_landing_code.py")):
        constants = assignments(directory / test_file)
        locators["sources"][repo] = {"sha": shas[repo], "file": test_file,
                                      **{key: {"value": constants[key][0], "line": constants[key][1]}
                                         for key in ("FORM_CONFIGS", "POPUP_BUTTON_CLASSES", "SERVICE_PLACE_VALUES")}}
        for path in sorted((directory / "config/providers").glob("*.py")):
            content = assignments(path)
            if "SITES" not in content:
                continue
            provider = content["PROVIDER"][0]
            for site in content["SITES"][0]:
                url = site["base_url"]
                relative = path.relative_to(directory).as_posix()
                add(repo, relative, content["SITES"][1], provider, url, "business_option", True,
                    "Candidate only: inspect forms for business controls; has_business=False does not exclude this path")
                if site.get("has_business"):
                    add(repo, relative, content["SITES"][1], provider, url.rstrip("/") + "/business", "business_page", True,
                        "Legacy generated /business path; source cities=" + repr(site.get("cities", site.get("city_name"))))
        if repo != "Big_landing_test":
            continue
        for path in sorted((directory / "urls").glob("*.txt")):
            for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                raw = line.strip()
                commented = raw.startswith("#")
                url = raw.lstrip("# ").split()[0] if raw.lstrip("# ") else ""
                if not url.startswith(("https://", "http://")):
                    continue
                add(repo, path.relative_to(directory).as_posix(), number, path.stem, url,
                    "business_page" if "/business" in urlsplit(url).path else "business_option", not commented,
                    "URL scope candidate; business control presence is not proven")
        for path in sorted((directory / "config/form_allowlists").glob("*.txt")):
            for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                raw = line.strip()
                url = raw.lstrip("# ").split()[0] if raw.lstrip("# ") else ""
                if url.startswith(("https://", "http://")):
                    inventory.append({"repo": repo, "sha": shas[repo], "path": path.relative_to(directory).as_posix(),
                                      "line": number, "url": url, "form_family": path.stem,
                                      "source_enabled": not raw.startswith("#"),
                                      "detail": "Form allowlist evidence, not proof of checkbox presence",
                                      "source_ref": f"https://github.com/deidolinde-maker/{repo}/blob/{shas[repo]}/{path.relative_to(directory).as_posix()}#L{number}"})

    grouped = {}
    for row in inventory:
        if "flow_kind" not in row:
            continue
        key = (row["provider"], row["url"], row["flow_kind"])
        grouped.setdefault(key, []).append(row)
    cases = []
    for (provider, url, flow), rows in sorted(grouped.items()):
        # These are onboarding records, never executable equivalence assertions.
        digest = hashlib.sha256(f"{provider}|{url}|{flow}".encode()).hexdigest()[:12]
        cases.append({"case_id": f"{provider}-{flow}-{digest}", "provider": provider,
                      "environment": "prod", "target_city": "Самара", "target_city_ui_id": "36401",
                      "flow_kind": flow, "source_page_url": url, "entry_url": None,
                      "status": "blocked", "region": None,
                      "reason": "Needs verified Samara route, exact form/control and submission region contract; source exclusions retained in inventory",
                      "source_refs": [r["source_ref"] for r in rows]})
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (("source_inventory.json", {"shas": shas, "records": inventory}),
                        ("locator_sources.json", locators), ("business_cases.json", {"schema_version": 1, "cases": cases})):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(inventory), len(cases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--everyday", type=Path, required=True)
    parser.add_argument("--big", type=Path, required=True)
    parser.add_argument("--everyday-sha", required=True)
    parser.add_argument("--big-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (args.output / "business_cases.json").exists():
        parser.error("output already has cases; import to a new directory and review changes")
    print(import_scope(args.everyday, args.big,
                       {"Everyday_test": args.everyday_sha, "Big_landing_test": args.big_sha}, args.output))
