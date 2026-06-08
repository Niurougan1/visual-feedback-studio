#!/usr/bin/env python3
"""Verify Visual Feedback Studio feedback application with conservative checks."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from source_resolution import resolve_edit_source_path


SCRIPT_DIR = Path(__file__).resolve().parent
PLAN_SCRIPT = SCRIPT_DIR / "plan_feedback_apply.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".", help="Project root to inspect")
    parser.add_argument("--feedback-file", help="Explicit feedback JSON file")
    parser.add_argument("--source-url", help="Prefer sessions matching this source URL or file path")
    parser.add_argument("--url", help="Optional local preview URL for browser verification")
    parser.add_argument("--preview-file", help="Use a saved preview JSON instead of generating one")
    parser.add_argument("--snapshot-file", help="Rollback snapshot JSON produced by apply_text_edits.py")
    parser.add_argument("--output", help="Verification output path; defaults to <project_root>/.visual_feedback_studio_verify.json")
    parser.add_argument("--artifacts-dir", help="Browser screenshot artifact directory; defaults to <project_root>/.visual_feedback_studio_artifacts")
    parser.add_argument("--no-write", action="store_true", help="Print verification without writing the result file")
    return parser.parse_args()


def load_plan(args: argparse.Namespace) -> dict[str, Any]:
    if args.preview_file:
        with Path(args.preview_file).expanduser().open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict) or not payload.get("ok"):
            raise RuntimeError("preview file is not a valid apply preview")
        return payload
    cmd = [sys.executable, str(PLAN_SCRIPT), args.project_root]
    if args.feedback_file:
        cmd.extend(["--feedback-file", args.feedback_file])
    if args.source_url:
        cmd.extend(["--source-url", args.source_url])
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"preview did not return JSON: {error}") from error
    if proc.returncode != 0 or not payload.get("ok"):
        raise RuntimeError(payload.get("error") or proc.stderr or "preview failed")
    return payload


def exact_count(haystack: str, needle: str) -> int:
    return 0 if not needle else haystack.count(needle)


def lifecycle_for_verify(status: str) -> str:
    if status == "verified":
        return "verified"
    if status == "manual_review":
        return "needs_review"
    return "unresolved"


def evidence_status(status: str) -> str:
    if status == "verified":
        return "passed"
    if status in {"drift", "not_found"}:
        return "failed"
    return "needs_review"


def read_source(path: Optional[str]) -> tuple[str, str]:
    if not path:
        return "", "selected feedback session does not resolve to a local source"
    source = Path(path)
    if not source.exists() or not source.is_file():
        return "", f"source file does not exist: {path}"
    try:
        return source.read_text(encoding="utf-8"), ""
    except UnicodeDecodeError:
        return "", f"source file is not utf-8 text: {path}"


def artifact_dir(root: Path, explicit: str = "") -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_absolute() else root / path
    return root / ".visual_feedback_studio_artifacts"


def rollback_command(root: Path, snapshot_file: str = "") -> str:
    if not snapshot_file:
        return ""
    return " ".join(shlex.quote(part) for part in [
        sys.executable,
        str(SCRIPT_DIR / "rollback_snapshot.py"),
        str(root.resolve()),
        "--snapshot",
        str(Path(snapshot_file).expanduser().resolve()),
    ])


def load_snapshot(path: str) -> dict[str, Any]:
    if not path:
        return {}
    snapshot_path = Path(path).expanduser().resolve()
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"snapshot_file": str(snapshot_path), "ok": False}
    if not isinstance(payload, dict) or payload.get("schema") != "visual_feedback_studio.rollback_snapshot.v1":
        return {"snapshot_file": str(snapshot_path), "ok": False}
    return {
        "ok": True,
        "snapshot_file": str(snapshot_path),
        "created_at": payload.get("created_at") or "",
        "entry_count": int(payload.get("entry_count") or len(payload.get("entries") or [])),
        "paths": [str(entry.get("path") or "") for entry in payload.get("entries", []) if isinstance(entry, dict)],
    }


def source_loc_line_status(item: dict[str, Any], source_text: str, source_path: Optional[Path], root: Path) -> tuple[str, str]:
    if not source_path:
        return "", ""
    try:
        from apply_policy import source_locs  # type: ignore
        from source_resolution import path_candidates
    except Exception:
        return "", ""
    original = str(item.get("original") or "")
    modified = str(item.get("modified") or "")
    if not modified:
        return "", ""
    lines = source_text.splitlines()
    for loc in source_locs(item):
        line = int(loc.get("line") or 0)
        if line <= 0 or line > len(lines):
            continue
        for candidate in path_candidates(str(loc.get("file") or ""), root):
            try:
                if candidate.resolve() != source_path.resolve():
                    continue
            except OSError:
                continue
            if modified in lines[line - 1]:
                if original and original in lines[line - 1]:
                    return "drift", "modified text found on sourceLoc line but original text is still present on that line"
                return "verified", "modified text found on sourceLoc line"
    return "", ""


def verify_text_source(plan: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    source_cache: dict[Path, tuple[str, str]] = {}
    for item in plan.get("text_edits", []):
        source_path, source_resolution = resolve_edit_source_path(item, root, plan.get("selected_source_path"))
        if source_path:
            if source_path not in source_cache:
                source_cache[source_path] = read_source(str(source_path))
            source_text, source_error = source_cache[source_path]
        else:
            source_text, source_error = "", source_resolution
        original = str(item.get("original") or "")
        modified = str(item.get("modified") or "")
        if source_error:
            status = "manual_review"
            reason = source_error
        else:
            source_loc_status, source_loc_reason = source_loc_line_status(item, source_text, source_path, root)
            if source_loc_status:
                status = source_loc_status
                reason = source_loc_reason
            elif modified and modified in source_text:
                original_count = exact_count(source_text, original)
                status = "verified" if original_count == 0 else "drift"
                reason = "modified text found" if status == "verified" else f"modified text found but original still appears {original_count} time(s)"
            else:
                status = "not_found"
                reason = "modified text was not found in selected source"
        results.append({
            "type": "text_edit",
            "selector": item.get("selector") or "",
            "evidence": "source_text",
            "status": status,
            "lifecycle_status": lifecycle_for_verify(status),
            "evidence_status": evidence_status(status),
            "reason": reason,
            "original": original,
            "modified": modified,
            "source_path": str(source_path) if source_path else "",
            "source_resolution": source_resolution,
        })
    return results


def verify_style_source(plan: dict[str, Any], source_text: str, source_error: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in plan.get("style_edits", []):
        selector = str(item.get("selector") or "")
        expected: list[str] = []
        for suggestion in item.get("suggestions", []):
            token = suggestion.get("token") if isinstance(suggestion.get("token"), dict) else {}
            if token.get("applied_as"):
                expected.append(str(token["applied_as"]))
            if token.get("name") and str(token["name"]).startswith("--"):
                expected.append(f"var({token['name']})")
            if suggestion.get("to"):
                expected.append(str(suggestion["to"]))
        if source_error:
            status = "manual_review"
            reason = source_error
        elif not expected:
            status = "manual_review"
            reason = "source-only mode has no concrete style values to verify"
        else:
            block = find_static_block(source_text, selector)
            if not block:
                status = "manual_review"
                reason = "selector block was not found uniquely in source-only mode"
            else:
                open_brace, close_brace = block
                block_text = source_text[open_brace + 1:close_brace]
                matched = [value for value in expected if value and value in block_text]
                status = "verified" if matched else "drift"
                reason = "expected style value or token was found in selector block" if matched else "expected style value or token was not found in selector block"
        results.append({
            "type": "style_edit",
            "selector": selector,
            "evidence": "source_selector_block",
            "status": status,
            "lifecycle_status": lifecycle_for_verify(status),
            "evidence_status": evidence_status(status),
            "reason": reason,
            "expected_values": sorted(set(expected)),
        })
    return results


def find_static_block(text: str, selector: str) -> tuple[int, int] | None:
    if not selector or "{" in selector or "}" in selector:
        return None
    pattern = re.compile(r"(^|\n)(?P<prefix>\s*)" + re.escape(selector) + r"\s*\{", re.MULTILINE)
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        return None
    open_brace = text.find("{", matches[0].start())
    depth = 0
    for index in range(open_brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return open_brace, index
    return None


def css_to_camel(name: str) -> str:
    return re.sub(r"-([a-z])", lambda match: match.group(1).upper(), name)


def safe_artifact_name(prefix: str, selector: str, suffix: str = "png") -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", selector or "page").strip("-")[:80] or "page"
    return f"{prefix}-{safe}.{suffix}"


def browser_verify(plan: dict[str, Any], url: str, artifacts: Path) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as error:
        return {
            "ok": True,
            "verification_mode": "browser_skipped",
            "reason": f"Playwright is not available: {error}",
            "results": [],
        }

    results: list[dict[str, Any]] = []
    artifacts.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page_screenshot = artifacts / safe_artifact_name(f"verify-{run_id}-page", "page")
        page.screenshot(path=str(page_screenshot), full_page=True)
        for item in plan.get("text_edits", []):
            selector = str(item.get("selector") or "")
            modified = str(item.get("modified") or "")
            try:
                locator = page.locator(selector).first if selector else None
                found = bool(locator and locator.count() > 0)
            except Exception as error:
                results.append({
                    "type": "text_edit",
                    "selector": selector,
                    "evidence": "browser_dom_text",
                    "status": "manual_review",
                    "lifecycle_status": "needs_review",
                    "evidence_status": "needs_review",
                    "reason": f"selector could not be evaluated: {error}",
                    "screenshot": str(page_screenshot),
                })
                continue
            if not found:
                results.append({"type": "text_edit", "selector": selector, "evidence": "browser_dom_text", "status": "not_found", "lifecycle_status": "unresolved", "evidence_status": "failed", "reason": "selector not found", "screenshot": str(page_screenshot)})
                continue
            assert locator is not None
            text = locator.text_content() or ""
            status = "verified" if modified in text else "drift"
            element_screenshot = artifacts / safe_artifact_name(f"verify-{run_id}-text", selector)
            try:
                locator.screenshot(path=str(element_screenshot))
            except Exception:
                element_screenshot = page_screenshot
            results.append({
                "type": "text_edit",
                "selector": selector,
                "evidence": "browser_dom_text",
                "status": status,
                "lifecycle_status": lifecycle_for_verify(status),
                "evidence_status": evidence_status(status),
                "reason": "modified text found in DOM" if modified in text else "modified text was not found in DOM",
                "actual_text": text,
                "screenshot": str(element_screenshot),
            })
        for item in plan.get("style_edits", []):
            selector = str(item.get("selector") or "")
            try:
                locator = page.locator(selector).first if selector else None
                found = bool(locator and locator.count() > 0)
            except Exception as error:
                results.append({
                    "type": "style_edit",
                    "selector": selector,
                    "evidence": "browser_computed_style",
                    "status": "manual_review",
                    "lifecycle_status": "needs_review",
                    "evidence_status": "needs_review",
                    "reason": f"selector could not be evaluated: {error}",
                    "screenshot": str(page_screenshot),
                })
                continue
            if not found:
                results.append({"type": "style_edit", "selector": selector, "evidence": "browser_computed_style", "status": "not_found", "lifecycle_status": "unresolved", "evidence_status": "failed", "reason": "selector not found", "screenshot": str(page_screenshot)})
                continue
            assert locator is not None
            checks: list[dict[str, str]] = []
            for suggestion in item.get("suggestions", []):
                prop = str(suggestion.get("property") or "")
                expected = str(suggestion.get("to") or "")
                if not prop or not expected:
                    continue
                actual = locator.evaluate("(el, prop) => window.getComputedStyle(el).getPropertyValue(prop)", prop)
                checks.append({"property": prop, "expected": expected, "actual": str(actual or "").strip()})
            status = "manual_review"
            reason = "no computed style checks available"
            if checks:
                matched = [check for check in checks if check["expected"] and check["expected"] in check["actual"]]
                status = "verified" if matched else "drift"
                reason = "computed style matched at least one expected value" if matched else "computed style did not match expected values"
            element_screenshot = artifacts / safe_artifact_name(f"verify-{run_id}-style", selector)
            try:
                locator.screenshot(path=str(element_screenshot))
            except Exception:
                element_screenshot = page_screenshot
            results.append({"type": "style_edit", "selector": selector, "evidence": "browser_computed_style", "status": status, "lifecycle_status": lifecycle_for_verify(status), "evidence_status": evidence_status(status), "reason": reason, "checks": checks, "screenshot": str(element_screenshot)})
        browser.close()
    return {"ok": True, "verification_mode": "browser", "url": url, "screenshot": str(page_screenshot), "artifacts_dir": str(artifacts), "results": results}


def output_path(args: argparse.Namespace) -> Path:
    if args.output:
        return Path(args.output).expanduser().resolve()
    return Path(args.project_root).expanduser().resolve() / ".visual_feedback_studio_verify.json"


def attach_failure_guidance(results: list[dict[str, Any]], rollback: str) -> None:
    for item in results:
        status = str(item.get("status") or "")
        if status in {"verified"}:
            continue
        next_steps = []
        if status == "drift":
            next_steps.append("Inspect this evidence item before committing; the source or browser state differs from the expected feedback.")
        elif status == "not_found":
            next_steps.append("Re-open a matching page/build or re-run feedback capture; the selector or source target was not found.")
        else:
            next_steps.append("Review manually; this feedback item does not have enough automated verification evidence.")
        if rollback:
            next_steps.append("Use rollback_command to restore the last applied source snapshot if this apply should be undone.")
            item["rollback_command"] = rollback
        item["next_steps"] = next_steps


def main() -> int:
    args = parse_args()
    try:
        root = Path(args.project_root).expanduser().resolve()
        plan = load_plan(args)
        source_text, source_error = read_source(plan.get("selected_source_path"))
        source_results = [
            *verify_text_source(plan, root),
            *verify_style_source(plan, source_text, source_error),
        ]
        for annotation in plan.get("annotations", []):
            source_results.append({
                "type": "annotation",
                "selector": annotation.get("selector") or "",
                "evidence": "annotation_intent",
                "status": "manual_review",
                "lifecycle_status": "needs_review",
                "evidence_status": "needs_review",
                "reason": "annotation verification requires human review unless it produced text/style changes",
                "note": annotation.get("note") or "",
            })
        browser_result = browser_verify(plan, args.url, artifact_dir(root, args.artifacts_dir or "")) if args.url else {"ok": True, "verification_mode": "source_only", "results": []}
        all_results = [*source_results, *browser_result.get("results", [])]
        snapshot = load_snapshot(args.snapshot_file or "")
        rollback = rollback_command(root, snapshot.get("snapshot_file") or "") if snapshot.get("ok") else ""
        attach_failure_guidance(all_results, rollback)
        counts: dict[str, int] = {}
        evidence_counts: dict[str, int] = {}
        for item in all_results:
            status = str(item.get("status") or "manual_review")
            counts[status] = counts.get(status, 0) + 1
            evidence = str(item.get("evidence_status") or evidence_status(status))
            evidence_counts[evidence] = evidence_counts.get(evidence, 0) + 1
        failed_count = counts.get("drift", 0) + counts.get("not_found", 0)
        needs_review_count = counts.get("manual_review", 0)
        payload = {
            "ok": True,
            "version": "4.0-beta",
            "report_schema": "visual_feedback_studio.verify_report.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "feedback_file": plan.get("feedback_file"),
            "selected_source_path": plan.get("selected_source_path"),
            "verification_mode": browser_result.get("verification_mode") or "source_only",
            "browser": browser_result,
            "counts": counts,
            "evidence_counts": evidence_counts,
            "summary": {
                "total": len(all_results),
                "verified": counts.get("verified", 0),
                "failed": failed_count,
                "needs_review": needs_review_count,
                "rollback_available": bool(rollback),
            },
            "snapshot": snapshot,
            "rollback_command": rollback,
            "results": all_results,
        }
        path = output_path(args)
        payload["output_file"] = str(path)
        if not args.no_write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
