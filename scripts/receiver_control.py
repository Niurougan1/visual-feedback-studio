#!/usr/bin/env python3
"""Start, inspect, and stop the Visual Feedback Studio receiver."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import signal
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib import parse
from urllib import error, request


SCRIPT_DIR = Path(__file__).resolve().parent
RECEIVER_JS = SCRIPT_DIR / "receiver.js"
ROOT_MARKERS = (
    "package.json",
    "index.html",
    "vite.config.js",
    "vite.config.ts",
    "next.config.js",
    "next.config.mjs",
    "astro.config.mjs",
    "svelte.config.js",
    "src",
    "app",
    "pages",
)
KNOWN_AGENTS = {"codex", "claude"}
TOKEN_BYTES = 24
TOKEN_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("project_root", nargs="?", default=".", help="Project root or source file path")
        p.add_argument("--host", default="127.0.0.1")
        p.add_argument("--port", type=int, default=3456)

    start = sub.add_parser("start", help="Start or reuse the receiver")
    add_common(start)
    start.add_argument("--agent", choices=sorted(KNOWN_AGENTS), help="Default agent for sessions without an explicit agent")
    start.add_argument("--feedback-file", help="Feedback file path; defaults to <project_root>/.visual_feedback_studio.json")
    start.add_argument("--tokens-file", help="Design token cache path; defaults to <project_root>/.visual_feedback_studio_tokens.json")
    start.add_argument(
        "--allowed-origin",
        action="append",
        default=[],
        help="Allow an additional remote preview origin, for example https://preview.example.com. May be passed more than once.",
    )
    start.add_argument("--timeout", type=float, default=5.0)

    status = sub.add_parser("status", help="Inspect receiver status")
    add_common(status)

    stop = sub.add_parser("stop", help="Stop the receiver recorded for this project")
    add_common(stop)

    return parser.parse_args()


def output(payload: dict[str, Any], code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


def resolve_project_root(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if path.is_file():
        path = path.parent
    current = path
    while True:
        if any((current / marker).exists() for marker in ROOT_MARKERS):
            return current
        if current.parent == current:
            return path
        current = current.parent


def state_file(project_root: Path) -> Path:
    return project_root / ".visual_feedback_studio_receiver.json"


def log_file(project_root: Path) -> Path:
    return project_root / ".visual_feedback_studio_receiver.log"


def log_tail(path: Path, limit: int = 4000) -> str:
    try:
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-limit:].strip()


def receiver_failure_next_step(log_text: str, host: str, port: int) -> str:
    lowered = log_text.lower()
    if "eaddrinuse" in lowered or "already in use" in lowered:
        return f"Port {port} is already in use. Rerun setup with VFS_PORT=<free-port> or stop the existing receiver."
    if "eperm" in lowered or "operation not permitted" in lowered:
        return f"This environment blocked binding {host}:{port}. Run setup from a normal terminal or allow the local receiver to bind a loopback port."
    return "Open the receiver log shown in log_file, or rerun setup with a different VFS_PORT if another local service may be using the port."


def feedback_file(project_root: Path, explicit: Optional[str]) -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_absolute():
            path = project_root / path
        return path.resolve()
    return (project_root / ".visual_feedback_studio.json").resolve()


def tokens_file(project_root: Path, explicit: Optional[str]) -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_absolute():
            path = project_root / path
        return path.resolve()
    return (project_root / ".visual_feedback_studio_tokens.json").resolve()


def preview_file(project_root: Path) -> Path:
    return (project_root / ".visual_feedback_studio_preview.json").resolve()


def verify_file(project_root: Path) -> Path:
    return (project_root / ".visual_feedback_studio_verify.json").resolve()


def requested_agent(args: argparse.Namespace) -> tuple[str, bool]:
    explicit = getattr(args, "agent", None)
    if explicit:
        return explicit, True
    raw = os.environ.get("VFS_AGENT", "").lower()
    if raw in KNOWN_AGENTS:
        return raw, True
    return "codex", False


def health_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/health"


def read_health(host: str, port: int, timeout: float = 0.7) -> Optional[dict[str, Any]]:
    try:
        with request.urlopen(health_url(host, port), timeout=timeout) as resp:
            if resp.status != 200:
                return None
            payload = json.loads(resp.read().decode("utf-8"))
            return payload if isinstance(payload, dict) and payload.get("ok") else None
    except (OSError, error.URLError, json.JSONDecodeError):
        return None


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_state(project_root: Path) -> dict[str, Any]:
    path = state_file(project_root)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def is_valid_token(token: Any) -> bool:
    value = str(token or "")
    return 12 <= len(value) <= 256 and all(char in TOKEN_CHARS for char in value)


def receiver_token(project_root: Path, feedback: Path, host: str, port: int) -> str:
    state = read_state(project_root)
    same_feedback = str(state.get("feedback_file") or "") == str(feedback)
    same_host = str(state.get("host") or "") == str(host)
    same_port = int(state.get("port") or port) == int(port)
    token = state.get("token")
    if same_feedback and same_host and same_port and is_valid_token(token):
        return str(token)
    return secrets.token_urlsafe(TOKEN_BYTES)


def write_state(project_root: Path, payload: dict[str, Any]) -> None:
    path = state_file(project_root)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def receiver_state(
    project_root: Path,
    host: str,
    port: int,
    feedback: Path,
    pid: Optional[int],
    running: bool,
    agent: str,
    token: str = "",
    tokens: Optional[Path] = None,
    allowed_origins: Optional[list[str]] = None,
) -> dict[str, Any]:
    return {
        "project_root": str(project_root),
        "host": host,
        "port": port,
        "url": f"http://{host}:{port}",
        "feedback_file": str(feedback),
        "tokens_file": str(tokens or tokens_file(project_root, None)),
        "preview_file": str(preview_file(project_root)),
        "verify_file": str(verify_file(project_root)),
        "agent": agent,
        "allowed_origins": allowed_origins or [],
        "token": token,
        "token_required": bool(token),
        "state_file": str(state_file(project_root)),
        "log_file": str(log_file(project_root)),
        "pid": pid,
        "running": running,
    }


def normalize_allowed_origins(values: list[str]) -> list[str]:
    origins: list[str] = []
    seen: set[str] = set()
    for raw in values:
        for item in str(raw or "").split(","):
            origin = item.strip().rstrip("/")
            if not origin or origin in seen:
                continue
            parsed = parse.urlparse(origin)
            if not parsed or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"allowed origin must be an http(s) origin, got: {origin}")
            normalized = f"{parsed.scheme}://{parsed.netloc}"
            if normalized not in seen:
                seen.add(normalized)
                origins.append(normalized)
    return origins


def start(args: argparse.Namespace) -> int:
    project_root = resolve_project_root(args.project_root)
    feedback = feedback_file(project_root, args.feedback_file)
    tokens = tokens_file(project_root, args.tokens_file)
    agent, agent_requested = requested_agent(args)
    allowed_origins = normalize_allowed_origins(args.allowed_origin)
    token = receiver_token(project_root, feedback, args.host, args.port)
    node_bin = shutil.which("node")
    if not node_bin:
        return output({
            "ok": False,
            "action": "failed",
            "error": "node is required to start the receiver but was not found in PATH",
            "next_step": "Install Node.js, or rerun setup from a shell where the node command is available.",
            "project_root": str(project_root),
            "host": args.host,
            "port": args.port,
        }, 127)
    existing = read_health(args.host, args.port)
    if existing:
        existing_feedback = str(Path(str(existing.get("feedback_file", ""))).resolve())
        desired_feedback = str(feedback)
        if existing_feedback == desired_feedback:
            existing_allowed = list(existing.get("allowed_origins") or [])
            missing_allowed = [origin for origin in allowed_origins if origin not in existing_allowed]
            if missing_allowed:
                return output({
                    "ok": False,
                    "action": "conflict",
                    "error": "receiver port is already serving this feedback file without the requested allowed remote origin",
                    "missing_allowed_origins": missing_allowed,
                    "existing_allowed_origins": existing_allowed,
                    "next_step": "Stop the old receiver or start this project on another port with the requested --allowed-origin value.",
                }, 2)
            existing_agent = str(existing.get("agent") or "codex")
            if agent_requested and existing_agent != agent:
                return output({
                    "ok": False,
                    "action": "conflict",
                    "error": "receiver port is already serving this feedback file with a different default agent",
                    "existing_agent": existing_agent,
                    "desired_agent": agent,
                    "next_step": "Stop the old receiver or start this project on another port and set localStorage.__vfs_port in the reviewed page.",
                }, 2)
            existing_state = read_state(project_root)
            state_token = str(existing_state.get("token") or "")
            if existing.get("token_required") and not is_valid_token(state_token):
                return output({
                    "ok": False,
                    "action": "conflict",
                    "error": "receiver requires a token but this project has no matching receiver token state",
                    "next_step": "Stop the old receiver or start this project on another port.",
                }, 2)
            payload = receiver_state(
                project_root,
                args.host,
                args.port,
                feedback,
                None,
                True,
                existing_agent,
                state_token if existing.get("token_required") else "",
                tokens,
                allowed_origins or existing.get("allowed_origins") or [],
            )
            payload.update({"ok": True, "action": "reused", "health": existing})
            write_state(project_root, payload)
            return output(payload)
        return output({
            "ok": False,
            "action": "conflict",
            "error": "receiver port is already serving a different feedback file",
            "existing_feedback_file": existing_feedback,
            "desired_feedback_file": desired_feedback,
            "next_step": "Stop the old receiver or start this project on another port and set localStorage.__vfs_port in the reviewed page.",
        }, 2)

    project_root.mkdir(parents=True, exist_ok=True)
    feedback.parent.mkdir(parents=True, exist_ok=True)
    log = log_file(project_root)
    log_handle = log.open("a", encoding="utf-8")
    env = {
        **os.environ,
        "VFS_HOST": args.host,
        "VFS_PORT": str(args.port),
        "VFS_FEEDBACK_FILE": str(feedback),
        "VFS_TOKENS_FILE": str(tokens),
        "VFS_PREVIEW_FILE": str(preview_file(project_root)),
        "VFS_VERIFY_FILE": str(verify_file(project_root)),
        "VFS_STATE_FILE": str(state_file(project_root)),
        "VFS_AGENT": agent,
        "VFS_TOKEN": token,
        "VFS_ALLOWED_ORIGINS": ",".join(allowed_origins),
    }
    proc = subprocess.Popen(
        [node_bin, str(RECEIVER_JS)],
        cwd=str(project_root),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        text=True,
    )
    log_handle.close()

    deadline = time.time() + args.timeout
    health = None
    while time.time() < deadline:
        if proc.poll() is not None:
            tail = log_tail(log)
            return output({
                "ok": False,
                "action": "failed",
                "error": "receiver exited before becoming healthy",
                "exit_code": proc.returncode,
                "log_file": str(log),
                "log_tail": tail,
                "next_step": receiver_failure_next_step(tail, args.host, args.port),
            }, 1)
        health = read_health(args.host, args.port, timeout=0.5)
        if health:
            break
        time.sleep(0.1)

    if not health:
        tail = log_tail(log)
        return output({
            "ok": False,
            "action": "timeout",
            "error": "receiver did not become healthy in time",
            "pid": proc.pid,
            "log_file": str(log),
            "log_tail": tail,
            "next_step": "The receiver process is still starting or blocked. Check log_tail/log_file, or rerun setup with --timeout 10.",
        }, 1)

    payload = receiver_state(project_root, args.host, args.port, feedback, proc.pid, True, str(health.get("agent") or agent), token, tokens, allowed_origins)
    payload.update({
        "ok": True,
        "action": "started",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "health": health,
    })
    write_state(project_root, payload)
    return output(payload)


def status(args: argparse.Namespace) -> int:
    project_root = resolve_project_root(args.project_root)
    state = read_state(project_root)
    host = state.get("host") or args.host
    port = int(state.get("port") or args.port)
    health = read_health(str(host), port)
    pid = state.get("pid")
    alive = process_alive(int(pid)) if isinstance(pid, int) else None
    return output({
        "ok": bool(health),
        "project_root": str(project_root),
        "state_file": str(state_file(project_root)),
        "state": state,
        "health": health,
        "pid_alive": alive,
    }, 0 if health else 1)


def stop(args: argparse.Namespace) -> int:
    project_root = resolve_project_root(args.project_root)
    state = read_state(project_root)
    pid = state.get("pid")
    if not isinstance(pid, int):
        return output({
            "ok": False,
            "action": "noop",
            "error": "no receiver pid recorded for this project",
            "state_file": str(state_file(project_root)),
        }, 1)

    if not process_alive(pid):
        return output({"ok": True, "action": "already_stopped", "pid": pid})

    os.kill(pid, signal.SIGTERM)
    deadline = time.time() + 3
    while time.time() < deadline:
        if not process_alive(pid):
            return output({"ok": True, "action": "stopped", "pid": pid})
        time.sleep(0.1)

    os.kill(pid, signal.SIGKILL)
    return output({"ok": True, "action": "killed", "pid": pid})


def main() -> int:
    args = parse_args()
    if args.port < 1 or args.port > 65535:
        return output({"ok": False, "error": "port must be between 1 and 65535"}, 2)
    if args.command == "start":
        return start(args)
    if args.command == "status":
        return status(args)
    if args.command == "stop":
        return stop(args)
    return output({"ok": False, "error": "unknown command"}, 2)


if __name__ == "__main__":
    raise SystemExit(main())
