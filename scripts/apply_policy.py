"""Shared conservative apply policy for Visual Feedback Studio text edits."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from source_resolution import path_candidates, source_loc_file


def exact_count(haystack: str, needle: str) -> int:
    return 0 if not needle else haystack.count(needle)


def lifecycle_for_text_status(status: str) -> str:
    if status == "auto_applicable":
        return "planned"
    if status == "unresolved":
        return "unresolved"
    return "needs_review"


def unresolved_next_steps(reason: str, confidence: str = "") -> list[str]:
    reason = str(reason or "")
    steps: list[str] = []
    if "outside project root" in reason:
        steps.append("Review the source path before allowing writes outside the project root.")
    elif "does not exist" in reason or "not resolve" in reason:
        steps.append("Open the page from a local dev build or provide --source-url/--feedback-file with a resolvable source.")
    elif "confidence is not high" in reason:
        steps.append("Prefer a dev build with sourceLoc/testId evidence, or review the candidate manually before editing.")
    elif "not found" in reason:
        steps.append("Search the project for nearby copy, component names, class names, and route context.")
    elif "appears" in reason:
        steps.append("Use source anchors, component context, or manual review to choose the intended occurrence.")
    elif "sequence-dependent" in reason or "overlaps another text edit" in reason:
        steps.append("Apply these overlapping text edits manually in source order, then rerun verify.")
    else:
        steps.append("Inspect source_hint, source_anchors, selector, and visible copy before changing source.")
    return steps


def text_edit_sequence_conflicts(edits: list[dict[str, Any]]) -> dict[int, str]:
    """Find text edits that could change each other's match counts.

    Preview and apply must agree before source is touched. When two edits have
    overlapping originals or one edit's replacement text introduces another
    edit's original text, automatic replacement becomes order-dependent.
    """
    conflicts: dict[int, str] = {}
    originals = [str(edit.get("original") or "") for edit in edits]
    modifieds = [str(edit.get("modified") or "") for edit in edits]

    def mark(left: int, right: int, detail: str) -> None:
        reason = f"sequence-dependent text edits: {detail}"
        conflicts.setdefault(left, reason)
        conflicts.setdefault(right, reason)

    for left, left_original in enumerate(originals):
        if not left_original:
            continue
        for right in range(left + 1, len(originals)):
            right_original = originals[right]
            if not right_original:
                continue
            if left_original in right_original or right_original in left_original:
                mark(left, right, "one original text overlaps another text edit")

    for source_index, modified in enumerate(modifieds):
        if not modified:
            continue
        for target_index, original in enumerate(originals):
            if source_index == target_index or not original:
                continue
            if original in modified:
                mark(source_index, target_index, "one replacement overlaps another text edit's original text")

    return conflicts


def _normalize_source_loc(source_loc: Any) -> Optional[dict[str, Any]]:
    if isinstance(source_loc, dict):
        file_value = source_loc_file(source_loc)
        if not file_value:
            return None
        try:
            line = int(source_loc.get("line") or 0)
        except (TypeError, ValueError):
            line = 0
        try:
            column = int(source_loc.get("column") or 0)
        except (TypeError, ValueError):
            column = 0
        return {"file": file_value, "line": line, "column": column}
    file_value = source_loc_file(source_loc)
    return {"file": file_value, "line": 0, "column": 0} if file_value else None


def source_locs(item: dict[str, Any]) -> list[dict[str, Any]]:
    locs: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()

    def add(raw: Any) -> None:
        normalized = _normalize_source_loc(raw)
        if not normalized:
            return
        key = (str(normalized["file"]), int(normalized["line"]), int(normalized["column"]))
        if key in seen:
            return
        seen.add(key)
        locs.append(normalized)

    anchors = item.get("source_anchors") if isinstance(item.get("source_anchors"), dict) else {}
    add(anchors.get("sourceLoc"))

    hint = item.get("source_hint") if isinstance(item.get("source_hint"), dict) else {}
    hint_anchors = hint.get("anchors") if isinstance(hint.get("anchors"), dict) else {}
    add(hint_anchors.get("sourceLoc"))

    chain = hint.get("component_chain") if isinstance(hint.get("component_chain"), list) else []
    for component in chain:
        if isinstance(component, dict):
            add(component.get("sourceLoc"))

    return locs


def _loc_matches_path(source_loc: dict[str, Any], source_path: Path, root: Path) -> bool:
    for candidate in path_candidates(str(source_loc.get("file") or ""), root):
        try:
            if candidate.resolve() == source_path.resolve():
                return True
        except OSError:
            continue
    return False


def source_loc_line_state(
    item: dict[str, Any],
    source_path: Optional[Path],
    root: Path,
    source_text: str,
    original: str,
    modified: str,
) -> dict[str, Any]:
    if not source_path:
        return {}
    lines = source_text.splitlines(keepends=True)
    matched_line = False
    for loc in source_locs(item):
        line = int(loc.get("line") or 0)
        if line <= 0:
            continue
        if not _loc_matches_path(loc, source_path, root):
            continue
        index = line - 1
        if index < 0 or index >= len(lines):
            continue
        matched_line = True
        line_text = lines[index]
        original_count = exact_count(line_text, original)
        modified_count = exact_count(line_text, modified)
        base = {"line": line, "column": int(loc.get("column") or 0)}
        if original_count and modified_count:
            return {**base, "state": "mixed", "line_match_count": original_count}
        if original_count == 1:
            return {**base, "state": "original_unique", "line_match_count": original_count}
        if original_count > 1:
            return {**base, "state": "original_ambiguous", "line_match_count": original_count}
        if modified_count:
            return {**base, "state": "already_modified", "modified_count": modified_count}
    return {"state": "sourceLoc_mismatch"} if matched_line else {}


def evaluate_text_edit(
    edit: dict[str, Any],
    source_text: str,
    source_error: str,
    source_path: Optional[Path],
    root: Path,
    sequence_conflict: str = "",
) -> dict[str, Any]:
    original = str(edit.get("original") or "")
    modified = str(edit.get("modified") or "")
    confidence = str(edit.get("locate_confidence") or "low")
    match_count = exact_count(source_text, original) if not source_error else 0
    line_state = {} if source_error else source_loc_line_state(edit, source_path, root, source_text, original, modified)
    status = "manual_review"
    reason = ""
    target: dict[str, Any] = {}

    if source_error:
        status = "unresolved"
        reason = source_error
    elif sequence_conflict:
        status = "manual_review"
        reason = sequence_conflict
    elif line_state.get("state") == "already_modified":
        status = "manual_review"
        reason = "sourceLoc line already contains modified text"
    elif line_state.get("state") == "mixed":
        status = "manual_review"
        reason = "sourceLoc line contains both original and modified text"
    elif match_count == 1:
        status = "auto_applicable"
        reason = "original text appears exactly once"
        target = {"strategy": "source_file_unique"}
    elif confidence == "high":
        if line_state.get("state") == "original_unique":
            status = "auto_applicable"
            reason = "high confidence and sourceLoc line contains original text exactly once"
            target = {
                "strategy": "sourceLoc_line_unique",
                "line": int(line_state.get("line") or 0),
                "column": int(line_state.get("column") or 0),
                "line_match_count": int(line_state.get("line_match_count") or 1),
            }
        elif line_state.get("state") == "original_ambiguous":
            status = "unresolved"
            reason = f"sourceLoc line contains original text {int(line_state.get('line_match_count') or 0)} times"
        elif line_state.get("state") == "sourceLoc_mismatch":
            status = "manual_review"
            reason = "sourceLoc line does not contain original text"
        elif match_count == 0:
            status = "unresolved"
            reason = "original text was not found in selected source"
        else:
            status = "unresolved"
            reason = f"original text appears {match_count} times"
    elif match_count == 0:
        status = "unresolved"
        reason = "original text was not found in selected source"
    else:
        status = "unresolved"
        reason = f"original text appears {match_count} times"

    return {
        "status": status,
        "lifecycle_status": lifecycle_for_text_status(status),
        "reason": reason,
        "reasons": [reason] if reason else [],
        "next_steps": [] if status == "auto_applicable" else unresolved_next_steps(reason, confidence),
        "match_count": match_count,
        "target": target,
    }


def replace_text_by_policy(source_text: str, original: str, modified: str, target: dict[str, Any]) -> str:
    if target.get("strategy") == "sourceLoc_line_unique":
        line = int(target.get("line") or 0)
        if line > 0:
            lines = source_text.splitlines(keepends=True)
            index = line - 1
            if 0 <= index < len(lines):
                lines[index] = lines[index].replace(original, modified, 1)
                return "".join(lines)
    return source_text.replace(original, modified, 1)
