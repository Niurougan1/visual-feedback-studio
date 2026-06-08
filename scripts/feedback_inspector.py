#!/usr/bin/env python3
"""Inspect Visual Feedback Studio feedback and emit a deterministic JSON summary."""

from __future__ import annotations

import argparse
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urlparse


FEEDBACK_NAMES = (".visual_feedback_studio.json", ".design_feedback.json")
CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}
LIFECYCLE_STATUSES = {"captured", "planned", "applied", "verified", "needs_review", "unresolved"}
EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".next",
    ".nuxt",
    ".svelte-kit",
    "dist",
    "build",
    "coverage",
    ".cache",
    ".parcel-cache",
    "__pycache__",
}

INTENT_KEYWORDS = {
    "spacing": ["挤", "太紧", "间距", "留白", "拥挤", "spacing", "tight", "crowded", "padding", "margin"],
    "contrast": ["看不清", "对比", "太淡", "不清楚", "contrast", "faint", "hard to read", "low contrast"],
    "hierarchy": ["层级", "重点", "不高级", "廉价", "主次", "hierarchy", "premium", "cheap", "emphasis"],
    "typography": ["字号", "字体", "行高", "标题", "typography", "font", "type", "headline"],
    "copy-tone": ["文案", "语气", "表达", "copy", "tone", "wording", "message"],
    "interaction": ["点击", "按钮", "行动", "吸引", "cta", "click", "button", "action"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".", help="Project root to inspect")
    parser.add_argument("--feedback-file", help="Explicit feedback JSON file")
    parser.add_argument("--source-url", help="Prefer sessions matching this source URL or file path")
    return parser.parse_args()


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def find_feedback_file(root: Path, explicit: Optional[str]) -> tuple[Optional[Path], list[dict[str, Any]]]:
    candidates: list[Path] = []
    trace: list[dict[str, Any]] = []

    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_absolute():
            path = root / path
        trace.append({"kind": "explicit", "path": str(path), "exists": path.exists()})
        return (path if path.exists() else None), trace

    for name in FEEDBACK_NAMES:
        path = root / name
        trace.append({"kind": "root", "path": str(path), "exists": path.exists()})
        if path.exists():
            return path, trace

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        if is_excluded(current.relative_to(root) if current != root else Path("")):
            continue
        for name in FEEDBACK_NAMES:
            if name in filenames:
                candidates.append(current / name)

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates[:10]:
        trace.append({"kind": "nested", "path": str(path), "mtime": path.stat().st_mtime})
    return (candidates[0] if candidates else None), trace


def source_url_to_path(source_url: str) -> Optional[str]:
    if not source_url:
        return None
    parsed = urlparse(source_url)
    if parsed.scheme == "file":
        return unquote(parsed.path)
    path = Path(source_url).expanduser()
    if path.exists():
        return str(path.resolve())
    return None


def session_ts(session: dict[str, Any]) -> str:
    return str(session.get("timestamp") or "")


def confidence_rank(change: dict[str, Any]) -> int:
    return CONFIDENCE_ORDER.get(str(change.get("locate_confidence") or "low"), 2)


def lifecycle_status(change: dict[str, Any], default: str = "captured") -> str:
    value = str(change.get("lifecycle_status") or change.get("status") or "").strip()
    return value if value in LIFECYCLE_STATUSES else default


def source_loc_key(source_loc: Any) -> str:
    if not isinstance(source_loc, dict):
        return ""
    file = str(source_loc.get("file") or "")
    line = str(source_loc.get("line") or "")
    column = str(source_loc.get("column") or "")
    return f"{file}:{line}:{column}" if file else ""


def source_hint(change: dict[str, Any]) -> dict[str, Any]:
    hint = change.get("source_hint") if isinstance(change.get("source_hint"), dict) else {}
    anchors = change.get("source_anchors") if isinstance(change.get("source_anchors"), dict) else {}
    if hint:
        merged = dict(hint)
        merged.setdefault("anchors", anchors)
        merged.setdefault("framework", "unknown")
        merged.setdefault("component_chain", [])
        merged.setdefault("dom_path", [])
        merged.setdefault("confidence_reasons", [])
        return merged
    return {
        "anchors": anchors,
        "framework": "unknown",
        "component_chain": [],
        "dom_path": [],
        "confidence_reasons": locate_reasons(anchors),
    }


def locate_reasons(anchors: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if anchors.get("testId"):
        reasons.append("testId")
    if anchors.get("sourceLoc"):
        reasons.append("sourceLoc")
    if anchors.get("stableId"):
        reasons.append("stableId")
    if anchors.get("componentName"):
        reasons.append("componentName")
    if anchors.get("role"):
        reasons.append("role")
    if anchors.get("ariaLabel"):
        reasons.append("ariaLabel")
    if not reasons and anchors.get("textFingerprint"):
        reasons.append("textFingerprint")
    if not reasons:
        reasons.append("selectorFallback")
    return reasons


def locate_summary(change: dict[str, Any]) -> str:
    hint = source_hint(change)
    anchors = hint.get("anchors") if isinstance(hint.get("anchors"), dict) else {}
    chain = hint.get("component_chain") if isinstance(hint.get("component_chain"), list) else []
    reasons = hint.get("confidence_reasons") if isinstance(hint.get("confidence_reasons"), list) else []
    parts: list[str] = []
    if anchors.get("testId"):
        parts.append(f"testId={anchors['testId']}")
    if anchors.get("sourceLoc"):
        parts.append(f"sourceLoc={source_loc_key(anchors.get('sourceLoc'))}")
    if chain:
        names = [str(item.get("name") or "") for item in chain if isinstance(item, dict) and item.get("name")]
        if names:
            parts.append("components=" + " > ".join(names[:4]))
    if anchors.get("componentName") and not chain:
        parts.append(f"component={anchors['componentName']}")
    if anchors.get("stableId"):
        parts.append(f"id={anchors['stableId']}")
    if not parts:
        parts.append("reasons=" + ",".join(str(reason) for reason in reasons))
    return "; ".join(part for part in parts if part)


def change_fingerprint(change: dict[str, Any]) -> str:
    anchors = change.get("source_anchors") if isinstance(change.get("source_anchors"), dict) else {}
    hint = source_hint(change)
    chain = hint.get("component_chain") if isinstance(hint.get("component_chain"), list) else []
    has_anchor_payload = any(value for value in anchors.values())
    if not has_anchor_payload and not chain:
        return "sel:" + str(change.get("selector") or "")
    test_id = str(anchors.get("testId") or "")
    if test_id:
        return f"tid:{test_id}"
    source_key = source_loc_key(anchors.get("sourceLoc"))
    if source_key:
        return f"src:{source_key}"
    chain_key = ">".join(str(item.get("name") or "") for item in chain if isinstance(item, dict) and item.get("name"))
    if chain_key:
        text = str(anchors.get("textFingerprint") or "")
        return f"chain:{chain_key}|{text[:80]}"
    stable_id = str(anchors.get("stableId") or "")
    if stable_id:
        return f"id:{stable_id}"
    component = str(anchors.get("componentName") or "")
    text = str(anchors.get("textFingerprint") or "")
    if component and text:
        return f"cmp:{component}|{text[:80]}"
    meta = change.get("element") if isinstance(change.get("element"), dict) else {}
    semantic = [
        str(meta.get("tag") or ""),
        str(anchors.get("role") or ""),
        str(text or meta.get("text") or "")[:80],
    ]
    if any(semantic):
        return "sem:" + "|".join(semantic)
    return "sel:" + str(change.get("selector") or "")


def guess_annotation_intent(note: str) -> str:
    lowered = str(note or "").lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return intent
    return ""


def enrich_annotation(change: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(change)
    enriched["source_hint"] = source_hint(enriched)
    enriched["locate_summary"] = locate_summary(enriched)
    if not enriched.get("intent_hint"):
        guess = guess_annotation_intent(str(enriched.get("note") or ""))
        if guess:
            enriched["intent_guess"] = guess
    return enriched


def load_feedback(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    sessions = data.get("sessions")
    if not isinstance(sessions, list):
        raise ValueError("feedback JSON must contain a sessions array")
    return data


def session_matches(session: dict[str, Any], source_url: Optional[str]) -> bool:
    if not source_url:
        return True
    wanted_path = source_url_to_path(source_url)
    actual_url = str(session.get("source_url") or "")
    actual_path = source_url_to_path(actual_url)
    return source_url == actual_url or (wanted_path is not None and wanted_path == actual_path)


def merge_style_edit(existing: Optional[dict[str, Any]], incoming: dict[str, Any]) -> dict[str, Any]:
    if existing is None:
        merged = deepcopy(incoming)
        merged["properties"] = {}
    else:
        merged = existing

    for key in [
        "timestamp",
        "source_url",
        "selector",
        "similar_selector",
        "batch",
        "batch_count",
        "computed_after",
        "element",
        "source_anchors",
        "source_hint",
        "locate_confidence",
        "locate_summary",
    ]:
        if key in incoming:
            merged[key] = deepcopy(incoming[key])

    if not merged.get("computed_before") and incoming.get("computed_before"):
        merged["computed_before"] = deepcopy(incoming["computed_before"])

    merged_props = merged.setdefault("properties", {})
    incoming_props = incoming.get("properties") or {}
    if not isinstance(incoming_props, dict):
        incoming_props = {}

    for prop, pair in incoming_props.items():
        prop_name = str(prop)
        if not prop_name:
            continue
        pair_payload = dict(pair) if isinstance(pair, dict) else {"modified": pair}
        previous = merged_props.get(prop_name)
        if isinstance(previous, dict) and "original" in previous:
            pair_payload["original"] = previous.get("original")
        else:
            pair_payload.setdefault("original", "")
        pair_payload.setdefault("modified", "")
        merged_props[prop_name] = pair_payload

    return merged


def summarize_sessions(sessions: list[dict[str, Any]], preferred_source: Optional[str]) -> dict[str, Any]:
    filtered = [s for s in sessions if session_matches(s, preferred_source)]
    if not filtered:
        filtered = sessions[:]

    filtered.sort(key=session_ts)
    latest = filtered[-1] if filtered else {}
    latest_source_url = str(latest.get("source_url") or "")

    same_source = [s for s in filtered if str(s.get("source_url") or "") == latest_source_url]
    if not same_source:
        same_source = filtered

    text_by_fingerprint: dict[str, dict[str, Any]] = {}
    style_by_fingerprint: dict[str, dict[str, Any]] = {}
    annotations: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for session in same_source:
        for change in session.get("changes") or []:
            if not isinstance(change, dict):
                continue
            enriched = dict(change)
            enriched["timestamp"] = session_ts(session)
            enriched["source_url"] = session.get("source_url", "")
            enriched["lifecycle_status"] = lifecycle_status(enriched)
            enriched["source_hint"] = source_hint(enriched)
            enriched["locate_summary"] = locate_summary(enriched)
            change_type = enriched.get("type")
            selector = str(enriched.get("selector") or "")
            if change_type == "text_edit" and selector:
                text_by_fingerprint[change_fingerprint(enriched)] = enriched
            elif change_type == "style_edit" and selector:
                fingerprint = change_fingerprint(enriched)
                style_by_fingerprint[fingerprint] = merge_style_edit(style_by_fingerprint.get(fingerprint), enriched)
            elif change_type == "annotation":
                annotations.append(enrich_annotation(enriched))
            else:
                unresolved.append(enriched)

    sort_key = lambda c: (confidence_rank(c), str(c.get("timestamp", "")), str(c.get("selector", "")))
    text_edits = sorted(text_by_fingerprint.values(), key=sort_key)
    style_edits = sorted(style_by_fingerprint.values(), key=sort_key)
    source_path = source_url_to_path(latest_source_url)

    source_counts: dict[str, dict[str, Any]] = {}
    for session in sessions:
        source_url = str(session.get("source_url") or "")
        item = source_counts.setdefault(source_url, {
            "source_url": source_url,
            "source_path": source_url_to_path(source_url),
            "session_count": 0,
            "change_count": 0,
            "latest_timestamp": "",
        })
        item["session_count"] += 1
        item["change_count"] += len(session.get("changes") or [])
        if session_ts(session) > item["latest_timestamp"]:
            item["latest_timestamp"] = session_ts(session)

    sources = sorted(source_counts.values(), key=lambda item: item["latest_timestamp"], reverse=True)

    return {
        "selected_source_url": latest_source_url,
        "selected_source_path": source_path,
        "selected_session_count": len(same_source),
        "latest_timestamp": session_ts(latest),
        "sources": sources,
        "merged": {
            "text_edits": text_edits,
            "style_edits": style_edits,
            "annotations": annotations,
            "unresolved_changes": unresolved,
        },
    }


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).expanduser().resolve()
    feedback_file, search_trace = find_feedback_file(root, args.feedback_file)

    if not feedback_file:
        print(json.dumps({
            "ok": False,
            "error": "No feedback file found",
            "project_root": str(root),
            "searched": search_trace,
        }, ensure_ascii=False, indent=2))
        return 2

    try:
        data = load_feedback(feedback_file)
        sessions = [s for s in data["sessions"] if isinstance(s, dict)]
        summary = summarize_sessions(sessions, args.source_url)
        result = {
            "ok": True,
            "project_root": str(root),
            "feedback_file": str(feedback_file.resolve()),
            "session_total": len(sessions),
            "search_trace": search_trace,
            **summary,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({
            "ok": False,
            "error": str(error),
            "feedback_file": str(feedback_file),
            "project_root": str(root),
        }, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
