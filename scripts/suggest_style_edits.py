#!/usr/bin/env python3
"""Suggest actionable CSS changes from Visual Feedback Studio style edits."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
INSPECTOR = SCRIPT_DIR / "feedback_inspector.py"
STATIC_SUFFIXES = {".css", ".html", ".htm"}
KEY_COMPUTED_PROPS = {
    "fontSize",
    "fontWeight",
    "lineHeight",
    "letterSpacing",
    "color",
    "backgroundColor",
    "padding",
    "paddingTop",
    "paddingRight",
    "paddingBottom",
    "paddingLeft",
    "margin",
    "marginTop",
    "marginRight",
    "marginBottom",
    "marginLeft",
    "borderRadius",
    "borderWidth",
    "borderStyle",
    "borderColor",
    "boxShadow",
    "width",
    "height",
    "opacity",
    "textAlign",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".", help="Project root to inspect")
    parser.add_argument("--feedback-file", help="Explicit feedback JSON file")
    parser.add_argument("--source-url", help="Prefer sessions matching this source URL or file path")
    parser.add_argument("--apply-static", action="store_true", help="Apply only uniquely resolvable static CSS/HTML selector blocks")
    parser.add_argument("--allow-outside-root", action="store_true", help="Allow --apply-static to write a static source outside project_root")
    return parser.parse_args()


def run_inspector(args: argparse.Namespace) -> dict[str, Any]:
    cmd = [sys.executable, str(INSPECTOR), args.project_root]
    if args.feedback_file:
        cmd.extend(["--feedback-file", args.feedback_file])
    if args.source_url:
        cmd.extend(["--source-url", args.source_url])
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"inspector did not return JSON: {error}") from error
    if proc.returncode != 0 or not payload.get("ok"):
        raise RuntimeError(payload.get("error") or proc.stderr or "inspector failed")
    return payload


def css_prop(name: str) -> str:
    value = str(name or "")
    if "-" in value:
        return value
    return re.sub(r"([A-Z])", lambda match: "-" + match.group(1).lower(), value)


def declaration(property_name: str, value: Any) -> str:
    return f"{css_prop(property_name)}: {str(value).strip()};"


def token_css_value(token: Any, fallback: str) -> tuple[str, Optional[dict[str, Any]]]:
    if not isinstance(token, dict):
        return fallback, None
    name = str(token.get("name") or "").strip()
    applied = str(token.get("applied_as") or "").strip()
    if name.startswith("--"):
        applied = applied or f"var({name})"
    if not applied:
        return fallback, dict(token)
    return applied, dict(token)


def computed_diff(edit: dict[str, Any]) -> list[dict[str, str]]:
    before = edit.get("computed_before") if isinstance(edit.get("computed_before"), dict) else {}
    after = edit.get("computed_after") if isinstance(edit.get("computed_after"), dict) else {}
    keys = sorted((set(before) | set(after)) & KEY_COMPUTED_PROPS)
    diff: list[dict[str, str]] = []
    for key in keys:
        old = str(before.get(key) or "")
        new = str(after.get(key) or "")
        if old != new:
            diff.append({"property": css_prop(key), "from": old, "to": new})
    return diff


def style_suggestions(edit: dict[str, Any]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    properties = edit.get("properties") if isinstance(edit.get("properties"), dict) else {}
    for prop, pair in sorted(properties.items()):
        payload = pair if isinstance(pair, dict) else {"modified": pair}
        modified = str(payload.get("modified") or "")
        if not modified:
            continue
        css_value, token = token_css_value(payload.get("token"), modified)
        suggestion: dict[str, Any] = {
            "property": css_prop(prop),
            "from": str(payload.get("original") or ""),
            "to": modified,
            "css": declaration(prop, css_value),
        }
        if token:
            suggestion["token"] = token
            suggestion["raw_css"] = declaration(prop, modified)
        suggestions.append(suggestion)
    return suggestions


def selector_comment(edit: dict[str, Any]) -> str:
    anchors = edit.get("source_anchors") if isinstance(edit.get("source_anchors"), dict) else {}
    component = str(anchors.get("componentName") or anchors.get("testId") or anchors.get("stableId") or "").strip()
    confidence = str(edit.get("locate_confidence") or "low")
    count = int(edit.get("batch_count") or 1)
    suffix = f" - {component}" if component else ""
    return f"{edit.get('selector') or '<unknown selector>'}{suffix} (confidence: {confidence}, affects {count})"


def css_preview_block(edit: dict[str, Any], suggestions: list[dict[str, Any]]) -> str:
    selector = str(edit.get("similar_selector") or edit.get("selector") or "").strip() or "/* unresolved selector */"
    lines = [f"/* {selector_comment(edit)} */", f"{selector} {{"]
    for suggestion in suggestions:
        old = f" /* was {suggestion['from']} */" if suggestion.get("from") else ""
        token = suggestion.get("token") if isinstance(suggestion.get("token"), dict) else {}
        raw = f" fallback {suggestion.get('raw_css')}" if token and suggestion.get("raw_css") else ""
        lines.append(f"  {suggestion['css']}{old}{raw}")
    lines.append("}")
    return "\n".join(lines)


def style_action_candidates(item: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    suggestions = item.get("suggestions") if isinstance(item.get("suggestions"), list) else []
    if suggestions:
        candidates.append({
            "kind": "style_source_suggestion",
            "label": "Map style edit to the owning class, component, prop, or design token",
            "target": item.get("similar_selector") or item.get("selector") or "",
            "confidence": item.get("locate_confidence") or "low",
            "auto_applicable": False,
            "properties": suggestions,
            "css_preview": item.get("css_preview") or "",
            "next_steps": [
                "Prefer existing design tokens, shared classes, component variants, or props over inline styles.",
                "Use --apply-static only for local static CSS/HTML with a uniquely located selector block.",
            ],
        })
    return candidates


def build_item(edit: dict[str, Any]) -> dict[str, Any]:
    suggestions = style_suggestions(edit)
    batch_count = int(edit.get("batch_count") or 1)
    batch = bool(edit.get("batch"))
    item: dict[str, Any] = {
        "type": "style_edit",
        "status": "manual_review",
        "lifecycle_status": "needs_review",
        "selector": edit.get("selector") or "",
        "similar_selector": edit.get("similar_selector") or "",
        "locate_confidence": edit.get("locate_confidence") or "low",
        "source_anchors": edit.get("source_anchors") or {},
        "source_hint": edit.get("source_hint") or {},
        "locate_summary": edit.get("locate_summary") or "",
        "batch": batch,
        "batch_count": batch_count,
        "suggestions": suggestions,
        "computed_diff": computed_diff(edit),
        "css_preview": css_preview_block(edit, suggestions),
    }
    if batch and batch_count > 1:
        tokenized = any(isinstance(suggestion.get("token"), dict) for suggestion in suggestions)
        token_hint = " or shared design token" if tokenized else ""
        item["batch_hint"] = f"Detected {batch_count} similar elements; prefer editing the shared class/component{token_hint} instead of one DOM node."
    item["action_candidates"] = style_action_candidates(item)
    return item


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


def declaration_pattern(property_name: str) -> re.Pattern[str]:
    prop = re.escape(css_prop(property_name))
    return re.compile(r"(?P<prefix>(?:^|[;\n])\s*)" + prop + r"\s*:\s*[^;\n{}]+;?", re.MULTILINE)


def append_declaration(body: str, decl: str) -> str:
    if not body.strip():
        return f"\n  {decl}\n"
    separator = "" if body.endswith("\n") else "\n"
    return f"{body}{separator}  {decl}\n"


def update_block_body(body: str, suggestions: list[dict[str, Any]]) -> tuple[str, list[str], list[dict[str, str]]]:
    updated = body
    applied: list[str] = []
    unresolved: list[dict[str, str]] = []
    for suggestion in suggestions:
        prop = css_prop(suggestion.get("property") or "")
        decl = suggestion.get("css") or declaration(prop, suggestion.get("to", ""))
        if not prop or not decl:
            continue
        matches = list(declaration_pattern(prop).finditer(updated))
        if len(matches) > 1:
            unresolved.append({"property": prop, "reason": "property declaration is not unique"})
            continue
        if len(matches) == 1:
            match = matches[0]
            replacement = f"{match.group('prefix')}{decl}"
            updated = updated[:match.start()] + replacement + updated[match.end():]
        else:
            updated = append_declaration(updated, decl)
        applied.append(decl)
    return updated, applied, unresolved


def is_inside_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def atomic_write_text(path: Path, text: str) -> None:
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def apply_static(summary: dict[str, Any], items: list[dict[str, Any]], root: Path, allow_outside_root: bool) -> dict[str, Any]:
    source_path = summary.get("selected_source_path")
    result = {"attempted": False, "applied": [], "unresolved": []}
    if not source_path:
        result["unresolved"].append({"reason": "selected source is not a local file"})
        return result
    path = Path(str(source_path))
    result["source_path"] = str(path)
    if not allow_outside_root and not is_inside_root(path, root):
        result["unresolved"].append({"reason": "source file is outside project root", "source_path": str(path)})
        return result
    if path.suffix.lower() not in STATIC_SUFFIXES or not path.exists() or not path.is_file():
        result["unresolved"].append({"reason": "selected source is not a static css/html file", "source_path": str(path)})
        return result
    text = path.read_text(encoding="utf-8")
    updated = text
    result["attempted"] = True
    for item in items:
        selector = str(item.get("similar_selector") or item.get("selector") or "")
        block = find_static_block(updated, selector)
        if not block:
            result["unresolved"].append({"selector": selector, "reason": "selector block not found uniquely"})
            continue
        open_brace, close_brace = block
        body = updated[open_brace + 1:close_brace]
        next_body, declarations, unresolved = update_block_body(body, item.get("suggestions", []))
        if unresolved:
            for problem in unresolved:
                result["unresolved"].append({"selector": selector, **problem})
        if declarations:
            updated = updated[:open_brace + 1] + next_body + updated[close_brace:]
            result["applied"].append({"selector": selector, "declarations": declarations})
    if updated != text:
        atomic_write_text(path, updated)
    return result


def main() -> int:
    args = parse_args()
    try:
        summary = run_inspector(args)
        edits = summary.get("merged", {}).get("style_edits", [])
        items = [build_item(edit) for edit in edits if isinstance(edit, dict)]
        result: dict[str, Any] = {
            "ok": True,
            "dry_run": not args.apply_static,
            "feedback_file": summary.get("feedback_file"),
            "source_path": summary.get("selected_source_path"),
            "style_suggestions": items,
            "css_preview": "\n\n".join(item["css_preview"] for item in items),
        }
        if args.apply_static:
            result["apply_static"] = apply_static(summary, items, Path(args.project_root).expanduser().resolve(), args.allow_outside_root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
