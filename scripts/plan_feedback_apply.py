#!/usr/bin/env python3
"""Preview how Visual Feedback Studio feedback can be applied without editing source files."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
INSPECTOR = SCRIPT_DIR / "feedback_inspector.py"
STYLE_SUGGEST = SCRIPT_DIR / "suggest_style_edits.py"
CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}

from apply_policy import evaluate_text_edit, text_edit_sequence_conflicts
from source_resolution import is_inside_root, resolve_edit_source_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".", help="Project root to inspect")
    parser.add_argument("--feedback-file", help="Explicit feedback JSON file")
    parser.add_argument("--source-url", help="Prefer sessions matching this source URL or file path")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    return parser.parse_args()


def run_json(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"command did not return JSON: {' '.join(cmd)}: {error}\n{proc.stdout}\n{proc.stderr}") from error
    if proc.returncode != 0 or not payload.get("ok"):
        raise RuntimeError(payload.get("error") or proc.stderr or "command failed")
    return payload


def inspector_payload(args: argparse.Namespace) -> dict[str, Any]:
    cmd = [sys.executable, str(INSPECTOR), args.project_root]
    if args.feedback_file:
        cmd.extend(["--feedback-file", args.feedback_file])
    if args.source_url:
        cmd.extend(["--source-url", args.source_url])
    return run_json(cmd)


def style_payload(args: argparse.Namespace) -> dict[str, Any]:
    cmd = [sys.executable, str(STYLE_SUGGEST), args.project_root]
    if args.feedback_file:
        cmd.extend(["--feedback-file", args.feedback_file])
    if args.source_url:
        cmd.extend(["--source-url", args.source_url])
    return run_json(cmd)


def read_source(path: Optional[str]) -> tuple[str, str]:
    if not path:
        return "", "selected feedback session does not resolve to a local file"
    source = Path(path)
    if not source.exists() or not source.is_file():
        return "", f"source file does not exist: {path}"
    try:
        return source.read_text(encoding="utf-8"), ""
    except UnicodeDecodeError:
        return "", f"source file is not utf-8 text: {path}"


def read_source_path(path: Optional[Path], fallback_error: str) -> tuple[str, str]:
    if not path:
        return "", fallback_error
    if not path.exists() or not path.is_file():
        return "", f"source file does not exist: {path}"
    try:
        return path.read_text(encoding="utf-8"), ""
    except UnicodeDecodeError:
        return "", f"source file is not utf-8 text: {path}"


def text_action_candidates(item: dict[str, Any]) -> list[dict[str, Any]]:
    status = str(item.get("status") or "")
    candidate: dict[str, Any] = {
        "kind": "replace_text",
        "label": "Replace visible copy in source",
        "target": item.get("source_path") or item.get("selector") or "",
        "confidence": item.get("locate_confidence") or "low",
        "auto_applicable": status == "auto_applicable",
        "diff": {
            "from": item.get("original") or "",
            "to": item.get("modified") or "",
        },
        "reasons": item.get("reasons") or [],
    }
    if status != "auto_applicable":
        candidate["next_steps"] = item.get("next_steps") or []
    return [candidate]


def style_action_candidates(item: dict[str, Any]) -> list[dict[str, Any]]:
    suggestions = item.get("suggestions") if isinstance(item.get("suggestions"), list) else []
    css_preview = str(item.get("css_preview") or "")
    candidates: list[dict[str, Any]] = []
    if suggestions:
        candidates.append({
            "kind": "style_source_suggestion",
            "label": "Map style edit to the owning class, component, prop, or design token",
            "target": item.get("selector") or "",
            "confidence": item.get("locate_confidence") or "low",
            "auto_applicable": False,
            "properties": suggestions,
            "css_preview": css_preview,
            "next_steps": [
                "Prefer existing design tokens, shared classes, component variants, or props over inline styles.",
                "If batch=true, apply the change to the shared source owner rather than one DOM occurrence.",
            ],
        })
    static_apply = item.get("static_apply") if isinstance(item.get("static_apply"), dict) else {}
    candidates.append({
        "kind": "apply_static_style",
        "label": "Apply only if a static CSS/HTML selector block is uniquely located",
        "target": item.get("selector") or "",
        "confidence": item.get("locate_confidence") or "low",
        "auto_applicable": False,
        "can_apply_static": bool(static_apply.get("can_apply_static")),
        "reason": static_apply.get("reason") or "",
        "command": "suggest_style_edits.py --apply-static",
    })
    return candidates


def annotation_action_candidates(item: dict[str, Any]) -> list[dict[str, Any]]:
    actions = item.get("concrete_actions") if isinstance(item.get("concrete_actions"), list) else []
    if not actions:
        actions = ["manual design review required"]
    return [
        {
            "kind": "annotation_intent",
            "label": action,
            "target": item.get("selector") or "",
            "confidence": "manual",
            "auto_applicable": False,
            "intent": item.get("intent") or "",
            "note": item.get("note") or "",
            "next_steps": [
                "Translate the note into a modest source change only when intent and target are clear.",
                "Keep the original note authoritative when intent_guess is only inferred.",
            ],
        }
        for action in actions
    ]


def text_plan(summary: dict[str, Any], root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    edits = [edit for edit in summary.get("merged", {}).get("text_edits", []) if isinstance(edit, dict)]
    sequence_conflicts = text_edit_sequence_conflicts(edits)
    for index, edit in enumerate(edits):
        resolved_source, source_resolution = resolve_edit_source_path(edit, root, summary.get("selected_source_path"))
        source_text, source_error = read_source_path(resolved_source, source_resolution)
        if resolved_source and not is_inside_root(resolved_source, root):
            source_error = f"source file is outside project root: {resolved_source}"
        original = str(edit.get("original") or "")
        modified = str(edit.get("modified") or "")
        confidence = str(edit.get("locate_confidence") or "low")
        if source_error:
            source_text = ""
        policy = evaluate_text_edit(edit, source_text, source_error, resolved_source, root, sequence_conflicts.get(index, ""))
        item = {
            "type": "text_edit",
            "status": policy["status"],
            "lifecycle_status": policy["lifecycle_status"],
            "selector": edit.get("selector") or "",
            "original": original,
            "modified": modified,
            "match_count": policy["match_count"],
            "locate_confidence": confidence,
            "source_path": str(resolved_source) if resolved_source else "",
            "source_resolution": source_resolution,
            "source_hint": edit.get("source_hint") or {},
            "locate_summary": edit.get("locate_summary") or "",
            "reasons": policy["reasons"],
            "apply_target": policy["target"],
        }
        item["next_steps"] = policy["next_steps"]
        item["action_candidates"] = text_action_candidates(item)
        items.append(item)
        if policy["status"] == "unresolved":
            unresolved.append(item)
    return items, unresolved


def annotation_plan(summary: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for annotation in summary.get("merged", {}).get("annotations", []):
        intent = annotation.get("intent_hint") or annotation.get("intent_guess") or ""
        snapshot = annotation.get("computed_snapshot") if isinstance(annotation.get("computed_snapshot"), dict) else {}
        concrete_actions: list[str] = []
        if intent == "spacing":
            concrete_actions.append("review spacing, padding, margin, line-height, and layout density")
        elif intent == "contrast":
            concrete_actions.append("review text/background contrast and visual weight")
        elif intent == "hierarchy":
            concrete_actions.append("review type scale, weight, color hierarchy, and grouping")
        elif intent == "typography":
            concrete_actions.append("review font size, line-height, weight, and wrapping")
        elif intent == "copy-tone":
            concrete_actions.append("rewrite copy while preserving meaning and product voice")
        elif intent == "interaction":
            concrete_actions.append("review CTA affordance, hover/active states, size, and contrast")
        else:
            concrete_actions.append("manual design review required")
        items.append({
            "type": "annotation",
            "status": "manual_review",
            "lifecycle_status": "needs_review",
            "selector": annotation.get("selector") or "",
            "note": annotation.get("note") or "",
            "intent": intent,
            "source_hint": annotation.get("source_hint") or {},
            "locate_summary": annotation.get("locate_summary") or "",
            "computed_summary": {key: snapshot.get(key) for key in ["fontSize", "fontWeight", "lineHeight", "color", "backgroundColor", "padding", "margin", "borderRadius"] if key in snapshot},
            "concrete_actions": concrete_actions,
        })
        items[-1]["action_candidates"] = annotation_action_candidates(items[-1])
    return items


def static_feasibility(source_path: Optional[str], selector: str) -> dict[str, Any]:
    if not source_path:
        return {"can_apply_static": False, "reason": "selected source is not a local file"}
    suffix = Path(source_path).suffix.lower()
    if suffix not in {".css", ".html", ".htm"}:
        return {"can_apply_static": False, "reason": "selected source is not static css/html"}
    if not selector:
        return {"can_apply_static": False, "reason": "missing selector"}
    return {"can_apply_static": True, "reason": "static source may be handled by suggest_style_edits.py --apply-static after confirmation"}


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    summary = inspector_payload(args)
    style = style_payload(args)
    root = Path(args.project_root).expanduser().resolve()
    text_items, unresolved = text_plan(summary, root)
    style_items: list[dict[str, Any]] = []
    for item in style.get("style_suggestions", []):
        selector = str(item.get("similar_selector") or item.get("selector") or "")
        style_items.append({
            "type": "style_edit",
            "status": "manual_review",
            "lifecycle_status": "needs_review",
            "selector": selector,
            "locate_confidence": item.get("locate_confidence") or "low",
            "source_hint": item.get("source_hint") or {},
            "locate_summary": item.get("locate_summary") or "",
            "batch": bool(item.get("batch")),
            "batch_count": int(item.get("batch_count") or 1),
            "suggestions": item.get("suggestions") or [],
            "computed_diff": item.get("computed_diff") or [],
            "css_preview": item.get("css_preview") or "",
            "batch_hint": item.get("batch_hint") or "",
            "static_apply": static_feasibility(summary.get("selected_source_path"), selector),
        })
        style_items[-1]["action_candidates"] = style_action_candidates(style_items[-1])
    annotations = annotation_plan(summary)
    counts = {
        "total": len(text_items) + len(style_items) + len(annotations),
        "auto_applicable_text": sum(1 for item in text_items if item["status"] == "auto_applicable"),
        "manual_review": sum(1 for item in [*text_items, *style_items, *annotations] if item["status"] == "manual_review"),
        "unresolved": len(unresolved),
    }
    return {
        "ok": True,
        "version": "4.0-beta",
        "dry_run": True,
        "feedback_file": summary.get("feedback_file"),
        "selected_source_url": summary.get("selected_source_url"),
        "selected_source_path": summary.get("selected_source_path"),
        "latest_timestamp": summary.get("latest_timestamp"),
        "counts": counts,
        "text_edits": text_items,
        "style_edits": style_items,
        "annotations": annotations,
        "unresolved": unresolved,
        "commands": {
            "apply_text_dry_run": " ".join(shlex.quote(part) for part in [sys.executable, str(SCRIPT_DIR / "apply_text_edits.py"), str(Path(args.project_root).expanduser().resolve()), "--dry-run"]),
            "style_suggestions": " ".join(shlex.quote(part) for part in [sys.executable, str(STYLE_SUGGEST), str(Path(args.project_root).expanduser().resolve())]),
        },
    }


def markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Visual Feedback Studio Apply Preview",
        "",
        f"- Feedback: `{plan.get('feedback_file')}`",
        f"- Source: `{plan.get('selected_source_path') or plan.get('selected_source_url')}`",
        f"- Total: {plan['counts']['total']}",
        f"- Auto-applicable text edits: {plan['counts']['auto_applicable_text']}",
        f"- Manual review: {plan['counts']['manual_review']}",
        f"- Unresolved: {plan['counts']['unresolved']}",
        "",
        "## Text Edits",
    ]
    for item in plan.get("text_edits", []):
        lines.append(f"- `{item['status']}` `{item['selector']}`: {item['original']!r} -> {item['modified']!r}")
    lines.append("")
    lines.append("## Style Edits")
    for item in plan.get("style_edits", []):
        lines.append(f"- `{item['status']}` `{item['selector']}` ({item['locate_confidence']})")
    lines.append("")
    lines.append("## Annotations")
    for item in plan.get("annotations", []):
        lines.append(f"- `{item.get('intent') or 'manual'}` `{item['selector']}`: {item['note']}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        plan = build_plan(args)
        if args.format == "markdown":
            print(markdown(plan))
        else:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
