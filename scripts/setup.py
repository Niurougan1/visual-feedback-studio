#!/usr/bin/env python3
"""One-command setup for Visual Feedback Studio."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


SKILL_NAME = "visual-feedback-studio"
BETA_SKILL_NAME = "visual-feedback-studio-beta"
BACKUP_ROOT = ".backups"
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
KNOWN_AGENTS = {"codex", "claude"}
RESTORE_AGENTS = {"codex", "claude", "both"}
CHANNELS = {"stable", "beta"}


def parse_args() -> argparse.Namespace:
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        parser = argparse.ArgumentParser(description="Restore a stable Visual Feedback Studio install from the latest backup.")
        parser.add_argument("command", choices=["restore"])
        parser.add_argument("project_root", nargs="?", default=".", help="Project root whose receiver should be stopped first")
        parser.add_argument("--agent", choices=sorted(RESTORE_AGENTS), default="both", help="Install target to restore")
        parser.add_argument("--codex-dir", help="Full Codex stable skill target directory")
        parser.add_argument("--claude-dir", help="Full Claude / Cowork stable skill target directory")
        parser.add_argument("--host", default="127.0.0.1")
        parser.add_argument("--port", type=int, default=3456)
        return parser.parse_args()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.set_defaults(command="setup")
    parser.add_argument("project_root", nargs="?", default=".", help="Project root to bind the receiver to")
    parser.add_argument("--agent", choices=sorted(KNOWN_AGENTS), default="codex", help="Receiver default agent")
    parser.add_argument("--channel", choices=sorted(CHANNELS), default="beta", help="Install channel. beta installs beside the stable skill by default.")
    parser.add_argument("--overwrite-stable", action="store_true", help="Allow replacing the stable install target")
    parser.add_argument(
        "--install",
        choices=["both", "codex", "claude", "none"],
        default="both",
        help="Install this skill package before starting the receiver",
    )
    parser.add_argument("--codex-dir", help="Full Codex skill target directory")
    parser.add_argument("--claude-dir", help="Full Claude / Cowork skill target directory")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3456)
    parser.add_argument("--feedback-file", help="Feedback file path; defaults to <project_root>/.visual_feedback_studio.json")
    parser.add_argument("--tokens-file", help="Design token cache path; defaults to <project_root>/.visual_feedback_studio_tokens.json")
    parser.add_argument("--scan-tokens", dest="scan_tokens", action="store_true", default=True, help="Scan project design tokens before starting the receiver")
    parser.add_argument("--no-scan-tokens", dest="scan_tokens", action="store_false", help="Skip design token scanning")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--skip-receiver", action="store_true", help="Only install and print extension instructions")
    return parser.parse_args()


def output(payload: dict[str, Any], code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


def channel_skill_name(channel: str) -> str:
    return BETA_SKILL_NAME if channel == "beta" else SKILL_NAME


def default_target(agent: str, channel: str = "stable") -> Path:
    name = channel_skill_name(channel)
    if agent == "codex":
        return Path.home() / ".codex" / "skills" / name
    return Path.home() / ".claude" / "skills" / name


def stable_target(agent: str, args: argparse.Namespace) -> Path:
    raw = args.codex_dir if agent == "codex" else args.claude_dir
    if not raw:
        return default_target(agent, "stable").resolve()
    target = Path(raw).expanduser().resolve()
    if target.name == BETA_SKILL_NAME:
        return target.with_name(SKILL_NAME).resolve()
    return target


def target_for(agent: str, args: argparse.Namespace) -> Path:
    raw = args.codex_dir if agent == "codex" else args.claude_dir
    if raw:
        return Path(raw).expanduser().resolve()
    if getattr(args, "overwrite_stable", False):
        return default_target(agent, "stable").resolve()
    return default_target(agent, args.channel).resolve()


def backup_dir(agent: str, stable: Path, timestamp: str) -> Path:
    return stable.parent / BACKUP_ROOT / SKILL_NAME / timestamp / agent


def install_agents(mode: str) -> list[str]:
    if mode == "none":
        return []
    if mode == "both":
        return ["codex", "claude"]
    return [mode]


def ignore_package_files(_dir: str, names: list[str]) -> set[str]:
    ignored = {
        ".git",
        ".DS_Store",
        ".pytest_cache",
        "__pycache__",
        "node_modules",
        ".next",
        "dist",
        "build",
        "coverage",
        "examples",
        "site-upload",
        ".visual_feedback_studio.json",
        ".design_feedback.json",
        ".visual_feedback_studio_tokens.json",
        ".visual_feedback_studio_preview.json",
        ".visual_feedback_studio_verify.json",
        ".visual_feedback_studio_snapshots",
        ".visual_feedback_studio_artifacts",
        ".visual_feedback_studio_receiver.json",
        ".visual_feedback_studio_receiver.log",
        "advanced-demo",
    }
    ignored.update(name for name in names if name.startswith("._"))
    return ignored.intersection(names)


def assert_safe_target(target: Path, channel: str = "stable") -> None:
    resolved = target.resolve()
    allowed = {BETA_SKILL_NAME} if channel == "beta" else {SKILL_NAME}
    if resolved.name not in allowed:
        raise ValueError(f"install target must end with one of {sorted(allowed)!r}: {resolved}")
    if str(resolved) in {"/", str(Path.home().resolve())}:
        raise ValueError(f"refusing unsafe install target: {resolved}")


def backup_stable_install(agent: str, target: Path, timestamp: str) -> Optional[dict[str, Any]]:
    stable = target.resolve()
    if not stable.exists():
        return None
    backup = backup_dir(agent, stable, timestamp).resolve()
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        shutil.rmtree(backup)
    shutil.copytree(stable, backup, ignore=ignore_package_files)
    return {"agent": agent, "source": str(stable), "backup": str(backup), "action": "backed_up"}


def copy_skill(target: Path, channel: str = "stable") -> dict[str, Any]:
    source = SKILL_DIR.resolve()
    target = target.resolve()
    assert_safe_target(target, channel)

    if source == target:
        return {"agent": "", "path": str(target), "action": "source"}

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=ignore_package_files)
    return {"agent": "", "path": str(target), "action": "installed"}


def install_skill(args: argparse.Namespace) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for agent in install_agents(args.install):
        backups: list[dict[str, Any]] = []
        stable = stable_target(agent, args)
        if stable.exists():
            backup = backup_stable_install(agent, stable, timestamp)
            if backup:
                backups.append(backup)
        target = target_for(agent, args)
        effective_channel = "stable" if args.overwrite_stable else args.channel
        if args.channel == "beta" and not args.overwrite_stable and target.name == SKILL_NAME:
            raise ValueError("beta channel refuses to install into the stable skill directory; use --channel stable or --overwrite-stable explicitly")
        result = copy_skill(target, effective_channel)
        result["agent"] = agent
        result["channel"] = effective_channel
        result["requested_channel"] = args.channel
        if backups:
            result["backups"] = backups
        results.append(result)
    return results


def preferred_runtime_dir(args: argparse.Namespace, installs: list[dict[str, Any]]) -> Path:
    by_agent = {str(item.get("agent")): Path(str(item.get("path"))) for item in installs if item.get("path")}
    if args.agent in by_agent:
        return by_agent[args.agent]
    if installs:
        return Path(str(installs[0]["path"]))
    return SKILL_DIR.resolve()


def run_receiver(args: argparse.Namespace, runtime_dir: Path) -> tuple[Optional[dict[str, Any]], int]:
    receiver_control = runtime_dir / "scripts" / "receiver_control.py"
    cmd = [
        sys.executable,
        str(receiver_control),
        "start",
        args.project_root,
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--agent",
        args.agent,
        "--timeout",
        str(args.timeout),
    ]
    if args.feedback_file:
        cmd.extend(["--feedback-file", args.feedback_file])
    if getattr(args, "tokens_file", None):
        cmd.extend(["--tokens-file", args.tokens_file])
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "action": "receiver_output_parse_failed",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    if proc.stderr:
        payload.setdefault("stderr", proc.stderr)
    return payload, proc.returncode


def run_token_scan(args: argparse.Namespace, runtime_dir: Path) -> Optional[dict[str, Any]]:
    if not getattr(args, "scan_tokens", False):
        return {"ok": True, "action": "skipped"}
    scanner = runtime_dir / "scripts" / "scan_design_tokens.py"
    if not scanner.exists():
        return {"ok": False, "action": "missing_scanner", "script": str(scanner)}
    cmd = [sys.executable, str(scanner), args.project_root]
    if getattr(args, "tokens_file", None):
        cmd.extend(["--output", args.tokens_file])
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"ok": False, "action": "token_scan_output_parse_failed", "stdout": proc.stdout}
    if proc.stderr:
        payload.setdefault("stderr", proc.stderr)
    payload.setdefault("returncode", proc.returncode)
    return payload


def extension_path(runtime_dir: Path) -> Path:
    return (runtime_dir / "chrome-extension").resolve()


def canonical_extension_path() -> Path:
    return (SKILL_DIR / "chrome-extension").resolve()


def extension_hint_path(runtime_dir: Path) -> Path:
    return runtime_dir.expanduser() / "chrome-extension"


def legacy_extension_hint_path(runtime_dir: Path) -> Path:
    return runtime_dir.expanduser() / "extension"


def stale_extension_paths(args: argparse.Namespace, canonical: Path) -> list[str]:
    candidates = [
        (SKILL_DIR / "extension").resolve(),
        (SKILL_DIR / "dist").resolve(),
        legacy_extension_hint_path(default_target(args.agent, "stable")),
        legacy_extension_hint_path(default_target(args.agent, "beta")),
        extension_hint_path(default_target(args.agent, "stable")),
        extension_hint_path(default_target(args.agent, "beta")),
    ]
    seen: set[str] = set()
    paths: list[str] = []
    for candidate in candidates:
        raw = str(candidate)
        if raw == str(canonical) or raw in seen:
            continue
        seen.add(raw)
        paths.append(raw)
    return paths


def status_command(runtime_dir: Path, project_root: str, host: str, port: int) -> str:
    script = runtime_dir / "scripts" / "receiver_control.py"
    parts = ["python3", str(script), "status", project_root, "--host", host, "--port", str(port)]
    return " ".join(shlex.quote(part) for part in parts)


def stop_command(runtime_dir: Path, project_root: str, host: str, port: int) -> str:
    script = runtime_dir / "scripts" / "receiver_control.py"
    parts = ["python3", str(script), "stop", project_root, "--host", host, "--port", str(port)]
    return " ".join(shlex.quote(part) for part in parts)


def rollback_command(project_root: str, agent: str, host: str, port: int) -> str:
    parts = ["python3", str(SCRIPT_DIR / "setup.py"), "restore", project_root, "--agent", agent, "--host", host, "--port", str(port)]
    return " ".join(shlex.quote(part) for part in parts)


def token_status(receiver_payload: Optional[dict[str, Any]]) -> str:
    if not receiver_payload:
        return "not-started"
    if not receiver_payload.get("ok"):
        return "unavailable"
    if receiver_payload.get("token_required") and receiver_payload.get("token"):
        return "required-and-configured"
    if receiver_payload.get("token_required"):
        return "required-but-missing"
    return "not-required"


def restore_agents(raw: str) -> list[str]:
    return ["codex", "claude"] if raw == "both" else [raw]


def latest_backup(stable: Path, agent: str) -> Optional[Path]:
    root = stable.parent / BACKUP_ROOT / SKILL_NAME
    if not root.exists():
        return None
    candidates = [path / agent for path in root.iterdir() if (path / agent).exists()]
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def restore_install(args: argparse.Namespace) -> int:
    results: list[dict[str, Any]] = []
    stop_results: list[dict[str, Any]] = []
    for agent in restore_agents(args.agent):
        stable = stable_target(agent, args)
        backup = latest_backup(stable, agent)
        if not backup:
            results.append({"agent": agent, "ok": False, "error": "no backup found", "stable_target": str(stable)})
            continue
        stop_script = stable / "scripts" / "receiver_control.py"
        if not stop_script.exists():
            stop_script = SCRIPT_DIR / "receiver_control.py"
        stop_proc = subprocess.run(
            [sys.executable, str(stop_script), "stop", args.project_root, "--host", args.host, "--port", str(args.port)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stop_payload = json.loads(stop_proc.stdout)
        except json.JSONDecodeError:
            stop_payload = {"ok": stop_proc.returncode == 0, "stdout": stop_proc.stdout, "stderr": stop_proc.stderr}
        stop_payload["agent"] = agent
        stop_results.append(stop_payload)
        if stable.exists():
            shutil.rmtree(stable)
        shutil.copytree(backup, stable, ignore=ignore_package_files)
        results.append({
            "agent": agent,
            "ok": True,
            "restored_path": str(stable),
            "backup_path": str(backup),
            "extension_load_unpacked": str(canonical_extension_path()),
        })
    ok = all(item.get("ok") for item in results) if results else False
    return output({
        "ok": ok,
        "action": "restore",
        "project_root": str(Path(args.project_root).expanduser().resolve()),
        "restored": results,
        "receiver_stop": stop_results,
        "next_steps": [
            "Reload chrome://extensions/ if the extension is already loaded.",
            "Load unpacked from extension_load_unpacked if Chrome asks for the extension folder again.",
        ],
    }, 0 if ok else 1)


def main() -> int:
    args = parse_args()
    if args.port < 1 or args.port > 65535:
        return output({"ok": False, "error": "port must be between 1 and 65535"}, 2)
    if getattr(args, "command", "setup") == "restore":
        return restore_install(args)

    try:
        installs = install_skill(args)
        runtime_dir = preferred_runtime_dir(args, installs)
        token_scan = run_token_scan(args, runtime_dir)
        receiver_payload: Optional[dict[str, Any]] = None
        receiver_code = 0
        if not args.skip_receiver:
            receiver_payload, receiver_code = run_receiver(args, runtime_dir)

        ok = receiver_code == 0 and (receiver_payload is None or bool(receiver_payload.get("ok")))
        ext = canonical_extension_path()
        payload = {
            "ok": ok,
            "action": "setup",
            "channel": args.channel,
            "skill_dir": str(SKILL_DIR.resolve()),
            "runtime_skill_dir": str(runtime_dir.resolve()),
            "project_root": str(Path(args.project_root).expanduser().resolve()),
            "install": {
                "mode": args.install,
                "targets": installs,
            },
            "token_scan": token_scan,
            "receiver": receiver_payload,
            "extension": {
                "path": str(ext),
                "chrome_url": "chrome://extensions/",
                "load_unpacked": str(ext),
                "store_manifest": str(ext / "manifest.json"),
                "permission_model": "activeTab + scripting + storage + optional host permissions",
                "store_permissions": ["activeTab", "scripting", "storage"],
                "optional_host_permissions": ["http://*/*", "https://*/*", "file:///*"],
                "file_url_note": "Enable Allow access to file URLs in the extension details when reviewing file:// pages.",
                "single_entry": True,
                "do_not_load": stale_extension_paths(args, ext),
            },
            "first_loop": {
                "target": "5-minute first loop",
                "receiver": "online" if ok else "offline",
                "token": token_status(receiver_payload),
                "steps": [
                    "Open chrome://extensions/ and keep one Visual Feedback Studio entry loaded from extension.load_unpacked.",
                    "Open or reload the target page, click Visual Feedback Studio, and grant the current site if the popup asks.",
                    "Click Start review / 开始审稿, capture feedback, then save.",
                    "Run the plan command from commands.plan.",
                ],
            },
            "next_steps": [
                "Open chrome://extensions/ and keep only one Visual Feedback Studio extension loaded from extension.load_unpacked.",
                "Open or reload the target page, click Visual Feedback Studio, then click Start review / 开始审稿.",
                "Save feedback in the page toolbar, then tell the current agent: 反馈好了.",
            ],
            "failure_guidance": {
                "receiver_offline": "Run the setup command again with --install none from the project root.",
                "token_mismatch": "Open the extension popup and click Refresh config, or restart the receiver.",
                "permission_missing": "Grant the current http/https origin in the popup. For file:// pages, enable Allow access to file URLs in extension details.",
            },
            "source_mapping_notes": [
                "High-precision sourceLoc is normally available from local development builds.",
                "Production builds may not expose sourceLoc; duplicate text will be left as needs_review or unresolved instead of guessed.",
                "Use scripts/self_check.py --strict-package after source-mapping changes.",
            ],
            "commands": {
                "status": status_command(runtime_dir, args.project_root, args.host, args.port),
                "doctor": " ".join(shlex.quote(part) for part in ["python3", str(runtime_dir / "scripts" / "vfs.py"), "doctor", args.project_root, "--host", args.host, "--port", str(args.port)]),
                "plan": " ".join(shlex.quote(part) for part in ["python3", str(runtime_dir / "scripts" / "vfs.py"), "plan", args.project_root]),
                "apply_verify": " ".join(shlex.quote(part) for part in ["python3", str(runtime_dir / "scripts" / "vfs.py"), "apply", args.project_root, "--verify"]),
                "stop": stop_command(runtime_dir, args.project_root, args.host, args.port),
                "rollback": rollback_command(args.project_root, "both", args.host, args.port),
            },
        }
        return output(payload, 0 if ok else max(receiver_code, 1))
    except Exception as exc:
        return output({"ok": False, "action": "setup_failed", "error": str(exc)}, 1)


if __name__ == "__main__":
    raise SystemExit(main())
