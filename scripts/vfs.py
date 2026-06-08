#!/usr/bin/env python3
"""Unified Visual Feedback Studio CLI facade.

This keeps the existing scripts as compatibility entry points while offering a
stable command shape for agents and future docs: plan/apply/verify/doctor/tokens.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
EXTENSION_DIR = SKILL_DIR / "chrome-extension"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Preview feedback application without editing source")
    add_project_args(plan)
    plan.add_argument("--format", choices=["json", "markdown"], default="json")

    apply = subparsers.add_parser("apply", help="Apply reliable source-proven text edits")
    add_project_args(apply)
    apply.add_argument("--dry-run", action="store_true", help="Report text edits without writing files")
    apply.add_argument("--allow-outside-root", action="store_true", help="Allow text edits outside project_root")
    apply.add_argument("--no-snapshot", action="store_true", help="Do not create a rollback snapshot before writing source files")
    apply.add_argument("--snapshot-dir", help="Rollback snapshot directory")
    apply.add_argument("--verify", action="store_true", help="Run verify after apply succeeds")
    apply.add_argument("--url", help="Optional local preview URL used with --verify")

    verify = subparsers.add_parser("verify", help="Verify source/browser state after feedback application")
    add_project_args(verify)
    verify.add_argument("--url", help="Optional local preview URL for browser verification")
    verify.add_argument("--preview-file", help="Use a saved preview JSON instead of generating one")
    verify.add_argument("--snapshot-file", help="Rollback snapshot JSON produced by apply")
    verify.add_argument("--output", help="Verification output path")
    verify.add_argument("--artifacts-dir", help="Browser screenshot artifact directory")
    verify.add_argument("--no-write", action="store_true", help="Print verification without writing result file")

    rollback = subparsers.add_parser("rollback", help="Restore files from an apply rollback snapshot")
    rollback.add_argument("project_root", nargs="?", default=".", help="Project root")
    rollback.add_argument("--snapshot", required=True, help="Snapshot JSON produced by apply")
    rollback.add_argument("--dry-run", action="store_true", help="Report files that would be restored without writing")
    rollback.add_argument("--force", action="store_true", help="Restore even if current file content differs from the recorded post-apply hash")
    rollback.add_argument("--allow-outside-root", action="store_true", help="Allow restoring paths outside project_root")

    doctor = subparsers.add_parser("doctor", help="Report receiver and feedback readiness")
    doctor.add_argument("project_root", nargs="?", default=".", help="Project root to inspect")
    doctor.add_argument("--host", default="127.0.0.1")
    doctor.add_argument("--port", type=int, default=3456)

    tokens = subparsers.add_parser("tokens", help="Design token utilities")
    token_subparsers = tokens.add_subparsers(dest="tokens_command", required=True)
    rescan = token_subparsers.add_parser("rescan", help="Rescan project design tokens")
    rescan.add_argument("project_root", nargs="?", default=".", help="Project root to scan")
    rescan.add_argument("--output", help="Token cache path")

    return parser.parse_args()


def add_project_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("project_root", nargs="?", default=".", help="Project root")
    parser.add_argument("--feedback-file", help="Explicit feedback JSON file")
    parser.add_argument("--source-url", help="Prefer sessions matching this source URL or file path")


def run_json(cmd: list[str]) -> tuple[int, dict[str, Any], str]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "error": "command did not return JSON",
            "command": cmd,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    if proc.stderr:
        payload.setdefault("stderr", proc.stderr)
    return proc.returncode, payload, proc.stdout


def print_payload(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def script_cmd(script_name: str, project_root: str, args: argparse.Namespace) -> list[str]:
    cmd = [sys.executable, str(SCRIPT_DIR / script_name), project_root]
    if getattr(args, "feedback_file", None):
        cmd.extend(["--feedback-file", args.feedback_file])
    if getattr(args, "source_url", None):
        cmd.extend(["--source-url", args.source_url])
    return cmd


def command_plan(args: argparse.Namespace) -> int:
    cmd = script_cmd("plan_feedback_apply.py", args.project_root, args)
    cmd.extend(["--format", args.format])
    code, payload, raw = run_json(cmd)
    if args.format == "markdown" and raw:
        print(raw, end="" if raw.endswith("\n") else "\n")
    else:
        payload.setdefault("cli_command", "plan")
        print_payload(payload)
    return code


def command_apply(args: argparse.Namespace) -> int:
    cmd = script_cmd("apply_text_edits.py", args.project_root, args)
    if args.dry_run:
        cmd.append("--dry-run")
    if args.allow_outside_root:
        cmd.append("--allow-outside-root")
    if args.no_snapshot:
        cmd.append("--no-snapshot")
    if args.snapshot_dir:
        cmd.extend(["--snapshot-dir", args.snapshot_dir])
    code, apply_payload, _raw = run_json(cmd)
    apply_payload.setdefault("cli_command", "apply")
    if code != 0 or not args.verify:
        print_payload(apply_payload)
        return code

    verify_cmd = script_cmd("verify_feedback_apply.py", args.project_root, args)
    if args.url:
        verify_cmd.extend(["--url", args.url])
    snapshot_file = str(apply_payload.get("snapshot_file") or "")
    if snapshot_file:
        verify_cmd.extend(["--snapshot-file", snapshot_file])
    verify_code, verify_payload, _verify_raw = run_json(verify_cmd)
    failed = int((verify_payload.get("summary") or {}).get("failed") or 0)
    needs_review = int((verify_payload.get("summary") or {}).get("needs_review") or 0)
    print_payload({
        "ok": bool(apply_payload.get("ok")) and bool(verify_payload.get("ok")) and failed == 0,
        "cli_command": "apply",
        "verified_after_apply": True,
        "report_schema": "visual_feedback_studio.apply_verify_report.v1",
        "verification_summary": verify_payload.get("summary") or {},
        "rollback_command": verify_payload.get("rollback_command") or apply_payload.get("rollback_command") or "",
        "needs_review": needs_review,
        "apply": apply_payload,
        "verify": verify_payload,
    })
    if verify_code != 0:
        return verify_code
    if code != 0:
        return code
    return 2 if failed > 0 else 0


def command_verify(args: argparse.Namespace) -> int:
    cmd = script_cmd("verify_feedback_apply.py", args.project_root, args)
    if args.url:
        cmd.extend(["--url", args.url])
    if args.preview_file:
        cmd.extend(["--preview-file", args.preview_file])
    if args.snapshot_file:
        cmd.extend(["--snapshot-file", args.snapshot_file])
    if args.output:
        cmd.extend(["--output", args.output])
    if args.artifacts_dir:
        cmd.extend(["--artifacts-dir", args.artifacts_dir])
    if args.no_write:
        cmd.append("--no-write")
    code, payload, _raw = run_json(cmd)
    payload.setdefault("cli_command", "verify")
    print_payload(payload)
    return code


def command_rollback(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "rollback_snapshot.py"),
        args.project_root,
        "--snapshot",
        args.snapshot,
    ]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.force:
        cmd.append("--force")
    if args.allow_outside_root:
        cmd.append("--allow-outside-root")
    code, payload, _raw = run_json(cmd)
    payload.setdefault("cli_command", "rollback")
    print_payload(payload)
    return code


def command_doctor(args: argparse.Namespace) -> int:
    status_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "receiver_control.py"),
        "status",
        args.project_root,
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    status_code, status_payload, _raw = run_json(status_cmd)
    feedback_cmd = [sys.executable, str(SCRIPT_DIR / "feedback_inspector.py"), args.project_root]
    feedback_code, feedback_payload, _feedback_raw = run_json(feedback_cmd)
    receiver_online = status_code == 0 and bool(status_payload.get("ok"))
    health = status_payload.get("health") or {}
    state = status_payload.get("state") or {}
    feedback_summary = health.get("feedback_summary") or {}
    preview_summary = health.get("preview_summary") or {}
    verify_summary = health.get("verify_summary") or {}
    token_required = bool(health.get("token_required") or state.get("token_required"))
    token_state = "required-and-configured" if token_required and state.get("token") else "required-but-missing" if token_required else "not-required"
    saved_count = int(feedback_summary.get("change_count") or 0)
    preview_ready = bool(preview_summary.get("exists") or health.get("last_preview_file"))
    verify_ready = bool(verify_summary.get("exists") or health.get("last_verify_file"))
    extension_path = EXTENSION_DIR.resolve()
    setup_command = " ".join(shlex_quote(part) for part in [
        "python3",
        str(SCRIPT_DIR / "setup.py"),
        args.project_root,
        "--install",
        "none",
        "--channel",
        "beta",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ])
    first_loop = [
        "Load exactly one extension from chrome-extension/.",
        "Open the target page, click Visual Feedback Studio, and grant the current site when prompted.",
        "Click Start review / 开始审稿, capture feedback, then save.",
        "Run `python3 scripts/vfs.py plan .` after the save.",
    ]
    if not receiver_online:
        next_steps = [f"Start the receiver: `{setup_command}`.", *first_loop[:2]]
    elif token_state == "required-but-missing":
        next_steps = [
            "Open the extension popup and click Refresh config.",
            "If the token still fails, restart the receiver with the setup command.",
        ]
    elif saved_count <= 0:
        next_steps = first_loop
    elif not preview_ready:
        next_steps = ["Run `python3 scripts/vfs.py plan .` to generate the apply preview."]
    elif not verify_ready:
        next_steps = ["Run `python3 scripts/vfs.py apply . --verify` or `python3 scripts/vfs.py verify .` after applying source changes."]
    else:
        next_steps = ["Review `.visual_feedback_studio_verify.json`; the feedback loop has receiver, preview, and verify evidence."]
    print_payload({
        "ok": receiver_online,
        "cli_command": "doctor",
        "version": "4.0-beta",
        "project_root": str(Path(args.project_root).expanduser().resolve()),
        "summary": {
            "receiver": "online" if receiver_online else "offline",
            "token": token_state,
            "feedback_count": saved_count,
            "preview_ready": preview_ready,
            "verify_ready": verify_ready,
            "permission_model": "activeTab + scripting + storage + optional host permissions",
        },
        "extension": {
            "load_unpacked": str(extension_path),
            "permission_model": "store-safe optional host permissions",
            "file_url_note": "Enable Allow access to file URLs in extension details before reviewing file:// pages.",
        },
        "receiver": status_payload,
        "feedback": feedback_payload if feedback_code == 0 else {
            "ok": False,
            "error": feedback_payload.get("error") or "No readable feedback file found",
        },
        "next_steps": next_steps,
        "failure_guidance": {
            "receiver_offline": f"Run `{setup_command}`.",
            "token_mismatch": "Open the extension popup and click Refresh config, or restart the receiver.",
            "permission_missing": "Grant the current http/https origin in the popup. For file:// pages, enable Allow access to file URLs in extension details.",
        },
    })
    return 0 if receiver_online else 1


def shlex_quote(value: str) -> str:
    import shlex
    return shlex.quote(str(value))


def command_tokens(args: argparse.Namespace) -> int:
    if args.tokens_command != "rescan":
        print_payload({"ok": False, "error": f"unknown tokens command: {args.tokens_command}"})
        return 2
    cmd = [sys.executable, str(SCRIPT_DIR / "scan_design_tokens.py"), args.project_root]
    if args.output:
        cmd.extend(["--output", args.output])
    code, payload, _raw = run_json(cmd)
    payload.setdefault("cli_command", "tokens rescan")
    print_payload(payload)
    return code


def main() -> int:
    args = parse_args()
    if args.command == "plan":
        return command_plan(args)
    if args.command == "apply":
        return command_apply(args)
    if args.command == "verify":
        return command_verify(args)
    if args.command == "rollback":
        return command_rollback(args)
    if args.command == "doctor":
        return command_doctor(args)
    if args.command == "tokens":
        return command_tokens(args)
    print_payload({"ok": False, "error": f"unknown command: {args.command}"})
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
