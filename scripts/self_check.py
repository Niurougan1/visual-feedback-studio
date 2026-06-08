#!/usr/bin/env python3
"""Run Visual Feedback Studio v4.0 beta smoke checks without external dependencies."""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Optional
from urllib import error, request


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EXTENSION = ROOT / "chrome-extension"
TEXT_SUFFIXES = {".html", ".js", ".json", ".md", ".py", ".txt", ".yaml", ".yml"}
ROOT_ALLOWED_FILES = {
    ".gitignore",
    "AGENTS.md",
    "CHANGELOG.md",
    "Logo.svg",
    "README.en.md",
    "README.md",
    "SKILL.md",
}
ROOT_ALLOWED_DIRS = {
    ".git",
    ".claude",
    ".local",
    "agents",
    "chrome-extension",
    "dist",
    "docs",
    "examples",
    "node_modules",
    "scripts",
}
DOCS_ALLOWED_ROOT_FILES = {
    "architecture.en.md",
    "architecture.md",
    "faq.en.md",
    "faq.md",
    "install.en.md",
    "install.md",
    "permissions.en.md",
    "permissions.md",
    "privacy.en.md",
    "privacy.md",
    "public-roadmap.en.md",
    "public-roadmap.md",
    "security.en.md",
    "security.md",
}
DOCS_ALLOWED_ROOT_DIRS: set[str] = set()
PACKAGE_EXCLUDED_PARTS = {
    ".git",
    "examples",
    "node_modules",
    "advanced-demo",
    "site-upload",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".visual_feedback_studio_snapshots",
    ".visual_feedback_studio_artifacts",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receiver", action="store_true", help="Also start the receiver and exercise receiver endpoints")
    parser.add_argument("--strict-package", action="store_true", help="Fail if package hygiene issues are found")
    parser.add_argument("--port", type=int, default=3458, help="Receiver smoke-test port")
    return parser.parse_args()


def run(cmd: list[str], cwd: Optional[Path] = None, env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(cwd or ROOT), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    return proc


def run_optional(cmd: list[str], cwd: Optional[Path] = None, env: Optional[dict[str, str]] = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd or ROOT), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def load_json(cmd: list[str], cwd: Optional[Path] = None, env: Optional[dict[str, str]] = None) -> dict[str, Any]:
    proc = run(cmd, cwd=cwd, env=env)
    return json.loads(proc.stdout)


def check_repository_layout() -> None:
    unexpected_root: list[str] = []
    for path in ROOT.iterdir():
        name = path.name
        if name.startswith("._") or name == ".DS_Store":
            continue
        if path.is_file() and name not in ROOT_ALLOWED_FILES:
            unexpected_root.append(name)
        elif path.is_dir() and name not in ROOT_ALLOWED_DIRS:
            unexpected_root.append(name + "/")
    if unexpected_root:
        raise AssertionError(f"unexpected root-level entries: {sorted(unexpected_root)}")

    if (ROOT / "extension").exists():
        raise AssertionError("legacy extension/ directory must not exist; use chrome-extension/")
    if not (ROOT / "chrome-extension" / "manifest.json").exists():
        raise AssertionError("chrome-extension/manifest.json is required")

    unexpected_docs: list[str] = []
    for path in (ROOT / "docs").iterdir():
        name = path.name
        if name.startswith("._") or name == ".DS_Store":
            continue
        if path.is_file() and name not in DOCS_ALLOWED_ROOT_FILES:
            unexpected_docs.append(name)
        elif path.is_dir() and name not in DOCS_ALLOWED_ROOT_DIRS:
            unexpected_docs.append(name + "/")
    if unexpected_docs:
        raise AssertionError(f"unexpected docs/ root entries: {sorted(unexpected_docs)}")


def check_js_and_json() -> None:
    run(["node", "--check", str(SCRIPTS / "receiver.js")])
    run(["node", "--check", str(EXTENSION / "hugeicons.js")])
    run(["node", "--check", str(EXTENSION / "vfs-helpers.js")])
    run(["node", "--check", str(EXTENSION / "inject.js")])
    run(["node", "--check", str(EXTENSION / "popup.js")])

    manifest = json.loads((EXTENSION / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 3
    assert manifest["name"] == "Visual Feedback Studio"
    assert manifest["version"] == "4.0.0"
    assert manifest["version_name"] == "4.0.0-beta"
    assert "beta" in manifest["description"].lower()
    assert manifest["permissions"] == ["activeTab", "scripting", "storage"]
    assert "host_permissions" not in manifest
    optional_hosts = set(manifest.get("optional_host_permissions") or [])
    assert {"http://*/*", "https://*/*", "file:///*"}.issubset(optional_hosts)

    inject = (EXTENSION / "inject.js").read_text(encoding="utf-8")
    assert "SESSION_VERSION = '4.0-beta'" in inject
    helper_source = (EXTENSION / "vfs-helpers.js").read_text(encoding="utf-8")
    assert "source_hint" in inject or "source_hint" in helper_source
    assert "getSourceHint" in helper_source
    assert "getSourcePayload" in helper_source
    assert "component_chain" in helper_source
    assert "dom_path" in helper_source
    assert "readReactFiberInfo" in helper_source
    assert "root.__VFS_HELPERS__" in helper_source
    assert "syncTokenCatalog" in inject
    assert "vf-token-chip" in inject
    assert "token" in inject
    assert "/apply-preview" in inject
    assert "/verify-result" in inject
    assert "refreshPreview" in inject
    assert "runVerify" in inject
    assert "attachShadow({ mode: 'closed' })" in inject
    assert "content: attr(data-tip)" in inject
    assert "source_anchors" in inject
    assert "locate_confidence" in inject
    assert "sourceSummary" in inject
    assert "getSourcePayload" in inject
    assert "vf-note-intent" in inject
    assert "tokenMismatch" in inject
    for forbidden in ["Tell Codex", "Back in Codex", "告诉 Codex", "回到 Codex"]:
        assert forbidden not in inject

    popup = (EXTENSION / "popup.js").read_text(encoding="utf-8")
    popup_html = (EXTENSION / "popup.html").read_text(encoding="utf-8")
    assert "v4.0 beta workspace" in popup
    assert "v4.0 beta 工作台" in popup_html
    assert 'data-i18n="footerRight"' in popup_html
    assert "python3 scripts/setup.py . --channel beta" in popup
    assert "refreshConfig" in popup
    assert "permissionPatternForUrl" in popup
    assert "chrome.permissions.request" in popup
    assert 'id="permission-row"' in popup_html
    assert 'id="permission-action"' in popup_html
    assert "receiver-actions" in popup_html
    assert "feedback_summary" in popup
    assert "reviewSaved" in popup
    assert 'id="review-row"' in popup_html
    assert "files: ['hugeicons.js', 'vfs-helpers.js', 'inject.js']" in popup
    assert '<script src="hugeicons.js"></script>' in popup_html


def check_single_extension_entrypoint() -> None:
    chrome_manifests: list[Path] = []
    for manifest in ROOT.rglob("manifest.json"):
        if any(part in {".git", "node_modules", "__pycache__"} for part in manifest.parts):
            continue
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("manifest_version") and payload.get("action", {}).get("default_popup"):
            chrome_manifests.append(manifest.resolve())
    expected = (EXTENSION / "manifest.json").resolve()
    if chrome_manifests != [expected]:
        raise AssertionError(f"Chrome extension must have one Load unpacked entry only: {chrome_manifests}")


def check_skill_metadata(strict_package: bool) -> list[str]:
    warnings: list[str] = []
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert skill.startswith("---\n")
    assert "\nname: visual-feedback-studio\n" in skill
    assert "\ndescription:" in skill
    assert "local-first" in skill
    assert "chrome-extension/" in skill
    assert "scripts/vfs.py" in skill
    assert "Internal planning" in skill

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "local-first" in readme
    assert "chrome-extension/" in readme
    assert "scripts/vfs.py" in readme
    assert "## 快速开始" in readme
    assert "## 它是什么" in readme
    assert readme.index("## 快速开始") < readme.index("## 它是什么")
    assert "内部计划" in readme
    assert "README.en.md" in readme

    english_readme = (ROOT / "README.en.md").read_text(encoding="utf-8")
    assert "## Quick Start" in english_readme
    assert "## What It Is" in english_readme
    assert english_readme.index("## Quick Start") < english_readme.index("## What It Is")
    assert "Internal planning" in english_readme

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "v4.0.0-beta" in changelog
    assert "v3.2.0-beta" in changelog

    for agent_file in ["openai.yaml", "anthropic.yaml"]:
        agent_yaml = (ROOT / "agents" / agent_file).read_text(encoding="utf-8")
        assert "display_name: \"Visual Feedback Studio\"" in agent_yaml
        assert "apply preview" in agent_yaml or "Preview" in agent_yaml
        assert "source_hint" in agent_yaml

    apple_double = [
        path for path in ROOT.rglob("._*")
        if ".git" not in path.parts and "examples" not in path.parts and "advanced-demo" not in path.parts and "site-upload" not in path.parts and "dist" not in path.parts
    ]
    if apple_double:
        message = f"AppleDouble files outside excluded demo/package paths: {[str(p) for p in apple_double]}"
        warnings.append(message)
    return warnings


def iter_text_files() -> list[Path]:
    paths: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in PACKAGE_EXCLUDED_PARTS for part in path.parts):
            continue
        if "docs" in path.parts:
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name == "SKILL.md":
            paths.append(path)
    return paths


def check_public_hygiene() -> None:
    def token(*codes: int) -> str:
        return "".join(chr(code) for code in codes)

    forbidden = [
        token(67, 111, 100, 101, 120, 32, 86, 105, 115, 117, 97, 108, 32, 66, 114, 105, 100, 103, 101),
        token(99, 111, 100, 101, 120, 45, 118, 105, 115, 117, 97, 108, 45, 98, 114, 105, 100, 103, 101),
        token(86, 105, 115, 117, 97, 108, 32, 66, 114, 105, 100, 103, 101),
        token(46, 99, 111, 100, 101, 120, 95, 118, 105, 115, 117, 97, 108, 95, 102, 101, 101, 100, 98, 97, 99, 107, 46, 106, 115, 111, 110),
        token(99, 111, 100, 101, 120, 95, 118, 105, 115, 117, 97, 108, 95, 98, 114, 105, 100, 103, 101),
        token(67, 86, 66, 95),
        token(95, 95, 99, 118, 98),
        token(90, 101, 114, 111, 45, 67, 111, 112, 121),
        token(90, 101, 114, 111, 32, 67, 111, 112, 121),
        token(108, 101, 120, 105, 101, 108, 105, 110),
        token(108, 101, 120, 105, 101, 108, 105, 110, 57, 57),
        token(103, 105, 116, 104, 117, 98, 46, 99, 111, 109),
        token(47, 116, 109, 112, 47, 90, 101, 114, 111),
    ]
    violations: list[str] = []
    for path in iter_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for item in forbidden:
            if item in text:
                violations.append(f"{path.relative_to(ROOT)} contains forbidden public token: {item}")
    if violations:
        raise AssertionError("; ".join(violations))


def check_python_ast() -> None:
    for path in [
        SCRIPTS / "feedback_inspector.py",
        SCRIPTS / "apply_text_edits.py",
        SCRIPTS / "apply_policy.py",
        SCRIPTS / "suggest_style_edits.py",
        SCRIPTS / "source_resolution.py",
        SCRIPTS / "scan_design_tokens.py",
        SCRIPTS / "plan_feedback_apply.py",
        SCRIPTS / "verify_feedback_apply.py",
        SCRIPTS / "vfs.py",
        SCRIPTS / "receiver_control.py",
        SCRIPTS / "setup.py",
        SCRIPTS / "package_extension.py",
        SCRIPTS / "install_browser_helper.py",
        SCRIPTS / "self_check.py",
    ]:
        ast.parse(path.read_text(encoding="utf-8"))

    verify_source = (SCRIPTS / "verify_feedback_apply.py").read_text(encoding="utf-8")
    assert ".first()" not in verify_source
    assert ".first if selector else None" in verify_source
    assert "selector block was not found uniquely" in verify_source
    assert "visual_feedback_studio.verify_report.v1" in verify_source
    assert "rollback_command" in verify_source
    assert ".visual_feedback_studio_artifacts" in verify_source
    assert "evidence_status" in verify_source
    assert "shlex.quote" in verify_source

    apply_source = (SCRIPTS / "apply_text_edits.py").read_text(encoding="utf-8")
    assert "evaluate_text_edit" in apply_source
    assert "replace_text_by_policy" in apply_source
    assert "resolve_edit_source_path" in apply_source
    assert "visual_feedback_studio.rollback_snapshot.v1" in apply_source
    assert ".visual_feedback_studio_snapshots" in apply_source
    assert "rollback_snapshot.py" in apply_source
    assert "shlex.quote" in apply_source

    rollback_source = (SCRIPTS / "rollback_snapshot.py").read_text(encoding="utf-8")
    assert "visual_feedback_studio.rollback_snapshot.v1" in rollback_source
    assert "current file differs from snapshot post-apply hash" in rollback_source
    assert "--force" in rollback_source

    policy_source = (SCRIPTS / "apply_policy.py").read_text(encoding="utf-8")
    assert "def evaluate_text_edit" in policy_source
    assert "original text appears exactly once" in policy_source
    assert "sourceLoc_line_unique" in policy_source
    assert "text_edit_sequence_conflicts" in policy_source

    plan_source = (SCRIPTS / "plan_feedback_apply.py").read_text(encoding="utf-8")
    assert "source_resolution" in plan_source
    assert "source file is outside project root" in plan_source
    assert "action_candidates" in plan_source
    assert "lifecycle_status" in plan_source
    assert "evaluate_text_edit" in plan_source
    assert "text_edit_sequence_conflicts" in plan_source

    vfs_source = (SCRIPTS / "vfs.py").read_text(encoding="utf-8")
    assert "subparsers.add_parser(\"plan\"" in vfs_source
    assert "subparsers.add_parser(\"apply\"" in vfs_source
    assert "subparsers.add_parser(\"verify\"" in vfs_source
    assert "subparsers.add_parser(\"rollback\"" in vfs_source
    assert "subparsers.add_parser(\"doctor\"" in vfs_source
    assert "--snapshot-file" in vfs_source
    assert "visual_feedback_studio.apply_verify_report.v1" in vfs_source
    assert "tokens rescan" in vfs_source

    resolution_source = (SCRIPTS / "source_resolution.py").read_text(encoding="utf-8")
    assert "def resolve_edit_source_path" in resolution_source
    assert "sourceLoc" in resolution_source

    style_source = (SCRIPTS / "suggest_style_edits.py").read_text(encoding="utf-8")
    assert "--allow-outside-root" in style_source
    assert "def is_inside_root" in style_source
    assert "def atomic_write_text" in style_source
    assert "action_candidates" in style_source
    assert "source file is outside project root" in style_source
    assert "selector block not found uniquely" in style_source

    receiver_source = (SCRIPTS / "receiver.js").read_text(encoding="utf-8")
    assert "/tokens/rescan" in receiver_source
    assert "feedback_summary" in receiver_source
    assert "summarizePreviewFile" in receiver_source
    assert "rollback_available" in receiver_source
    assert "evidence_counts" in receiver_source

    setup_source = (SCRIPTS / "setup.py").read_text(encoding="utf-8")
    assert "source_mapping_notes" in setup_source
    assert "doctor" in setup_source
    assert "apply_verify" in setup_source
    assert "first_loop" in setup_source
    assert "permission_model" in setup_source
    assert "optional_host_permissions" in setup_source
    assert "token_mismatch" in setup_source
    assert "auto_misapply_count" in setup_source
    assert ".visual_feedback_studio_snapshots" in setup_source
    assert ".visual_feedback_studio_artifacts" in setup_source


def check_extension_helpers() -> None:
    script = r"""
require('./chrome-extension/vfs-helpers.js');
const helperRef = globalThis.__VFS_HELPERS__;
require('./chrome-extension/inject.js');
const helpers = globalThis.__VFS_HELPERS__;
function element(attrs = {}, opts = {}) {
  return {
    id: opts.id || '',
    textContent: opts.text || '',
    parentElement: opts.parent || null,
    nodeType: 1,
    tagName: opts.tagName || 'DIV',
    classList: opts.classList || [],
    getAttribute(name) {
      return Object.prototype.hasOwnProperty.call(attrs, name) ? attrs[name] : '';
    }
  };
}
const parent = element({ 'data-source': 'src/Hero.tsx:12:7' }, { tagName: 'SECTION', text: 'Parent' });
const target = element({
  'data-testid': 'hero-title',
  role: 'heading',
  'aria-label': 'Hero title',
  'data-component': 'HeroTitle'
}, { id: 'hero-title', text: '  Hero   Title  ', parent, tagName: 'H1', classList: ['title'] });
const fiberTarget = element({}, { id: 'fiber-title', text: 'Fiber Title', tagName: 'H1' });
fiberTarget.__reactFiber$test = {
  elementType: { displayName: 'HeroTitle' },
  _debugSource: { fileName: 'src/Hero.tsx', lineNumber: 21, columnNumber: 5 },
  return: {
    elementType: { name: 'HeroSection' },
    _debugSource: { fileName: 'src/Hero.tsx', lineNumber: 18, columnNumber: 3 },
    return: null
  }
};
const anchors = helpers.getSourceAnchors(target);
const hint = helpers.getSourceHint(target, anchors);
const plain = helpers.getSourceHint(element({}, { text: 'Plain DOM' }));
const fiberInfo = helpers.readReactFiberInfo(fiberTarget);
const fiberAnchors = helpers.getSourceAnchors(fiberTarget);
const fiberHint = helpers.getSourceHint(fiberTarget, fiberAnchors);
const fiberPayload = helpers.getSourcePayload(fiberTarget);
console.log(JSON.stringify({
  sameHelperObject: helperRef === helpers,
  anchors,
  hint,
  plain,
  fiberInfo,
  fiberAnchors,
  fiberHint,
  fiberPayload,
  high: helpers.locateConfidence(anchors),
  low: helpers.locateConfidence({}),
  stableGood: helpers.isStableId('hero-title'),
  stableBad: helpers.isStableId('react-select-123'),
  sourceLoc: helpers.normalizeSourceLoc('src/App.tsx:8:3'),
  parsedPx: helpers.parseControlNumber('72px'),
  parsedComma: helpers.parseControlNumber('1,5'),
  parsedBad: helpers.parseControlNumber('nope'),
  clamped: helpers.clampControlNumber({ min: 0, max: 10 }, 18),
  hex: helpers.rgbToHex('rgb(17, 34, 51)')
}));
"""
    payload = json.loads(run(["node", "-e", script]).stdout)
    assert payload["sameHelperObject"] is True
    anchors = payload["anchors"]
    assert anchors["testId"] == "hero-title"
    assert anchors["stableId"] == "hero-title"
    assert anchors["sourceLoc"] == {"file": "src/Hero.tsx", "line": 12, "column": 7}
    assert anchors["textFingerprint"] == "Hero Title"
    assert anchors["role"] == "heading"
    assert anchors["ariaLabel"] == "Hero title"
    assert anchors["componentName"] == "HeroTitle"
    assert payload["hint"]["framework"] == "unknown"
    assert payload["hint"]["component_chain"][0]["name"] == "HeroTitle"
    assert payload["hint"]["dom_path"][0]["tag"] == "h1"
    assert "componentChain" in payload["hint"]["confidence_reasons"]
    assert payload["plain"]["framework"] == "unknown"
    assert payload["fiberInfo"]["debugSource"] == {"file": "src/Hero.tsx", "line": 21, "column": 5}
    assert payload["fiberInfo"]["componentName"] == "HeroTitle"
    assert [item["name"] for item in payload["fiberInfo"]["componentChain"]] == ["HeroTitle", "HeroSection"]
    assert payload["fiberAnchors"]["sourceLoc"] == {"file": "src/Hero.tsx", "line": 21, "column": 5}
    assert payload["fiberAnchors"]["componentName"] == "HeroTitle"
    assert payload["fiberHint"]["framework"] == "react"
    assert payload["fiberHint"]["component_chain"][0]["name"] == "HeroTitle"
    assert payload["fiberPayload"]["locate_confidence"] == "high"
    assert payload["fiberPayload"]["source_anchors"]["sourceLoc"] == {"file": "src/Hero.tsx", "line": 21, "column": 5}
    assert payload["fiberPayload"]["source_hint"]["framework"] == "react"
    assert payload["fiberPayload"]["source_hint"]["component_chain"][1]["name"] == "HeroSection"
    assert payload["low"] == "low"
    assert payload["stableGood"] is True
    assert payload["stableBad"] is False
    assert payload["sourceLoc"] == {"file": "src/App.tsx", "line": 8, "column": 3}
    assert payload["parsedPx"] == 72
    assert payload["parsedComma"] == 1.5
    assert payload["parsedBad"] is None
    assert payload["clamped"] == 10
    assert payload["hex"] == "#112233"


def write_feedback(project: Path, source: Path, *, duplicate: bool = False, text_confidence: str = "high") -> Path:
    feedback = project / ".visual_feedback_studio.json"
    source_hint = {
        "anchors": {
            "testId": "hero-title",
            "stableId": "",
            "sourceLoc": {"file": "src/Hero.tsx", "line": 12, "column": 7},
            "textFingerprint": "Old headline",
            "role": "heading",
            "ariaLabel": "Hero title",
            "componentName": "HeroTitle",
        },
        "framework": "react",
        "component_chain": [{"name": "HeroTitle", "framework": "react", "sourceLoc": {"file": "src/Hero.tsx", "line": 12, "column": 7}}],
        "dom_path": [{"tag": "h1", "testId": "hero-title", "text": "Old headline"}],
        "confidence_reasons": ["testId", "sourceLoc", "componentChain"],
    }
    source_anchors = source_hint["anchors"]
    payload = {
        "sessions": [
            {
                "timestamp": "2026-06-04T10:00:00.000Z",
                "version": "3.2-beta",
                "agent": "codex",
                "source_url": source.as_uri(),
                "page_title": "Smoke",
                "viewport": {"width": 1440, "height": 900},
                "changes": [
                    {
                        "type": "text_edit",
                        "selector": "h1.hero",
                        "original": "Old headline",
                        "modified": "New headline",
                        "source_anchors": source_anchors,
                        "source_hint": source_hint,
                        "locate_confidence": text_confidence,
                    },
                    {
                        "type": "style_edit",
                        "selector": ".cta",
                        "similar_selector": ".cta",
                        "batch": True,
                        "batch_count": 3,
                        "properties": {
                            "padding-left": {
                                "original": "16px",
                                "modified": "16px",
                                "token": {
                                    "name": "--space-4",
                                    "value": "16px",
                                    "type": "spacing",
                                    "source": "styles.css",
                                    "distance": 0,
                                    "applied_as": "var(--space-4)",
                                },
                            },
                            "border-radius": {"original": "4px", "modified": "8px"},
                        },
                        "computed_before": {"paddingLeft": "8px", "borderRadius": "4px"},
                        "computed_after": {"paddingLeft": "16px", "borderRadius": "8px"},
                        "source_anchors": {"testId": "primary-cta", "textFingerprint": "Join"},
                        "locate_confidence": "high",
                    },
                    {
                        "type": "annotation",
                        "selector": ".cta",
                        "note": "按钮没有点击欲望",
                        "computed_snapshot": {"fontSize": "14px", "backgroundColor": "#f0f0f0", "borderRadius": "4px"},
                        "source_anchors": {"testId": "primary-cta", "textFingerprint": "Join"},
                        "locate_confidence": "high",
                    },
                ],
            }
        ]
    }
    if duplicate:
        source.write_text('<h1 class="hero">Old headline</h1><p>Old headline</p><button class="cta">Join</button>', encoding="utf-8")
    feedback.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return feedback


def write_sourceloc_feedback(project: Path, page_source: Path, source_loc_file: str) -> Path:
    feedback = project / ".visual_feedback_studio.json"
    source_loc = {"file": source_loc_file, "line": 3, "column": 12}
    source_hint = {
        "anchors": {
            "testId": "hero-title",
            "sourceLoc": source_loc,
            "textFingerprint": "Old headline",
            "componentName": "HeroTitle",
        },
        "framework": "react",
        "component_chain": [{"name": "HeroTitle", "framework": "react", "sourceLoc": source_loc}],
        "dom_path": [{"tag": "h1", "testId": "hero-title", "text": "Old headline"}],
        "confidence_reasons": ["testId", "sourceLoc", "componentChain"],
    }
    payload = {
        "sessions": [
            {
                "timestamp": "2026-06-04T10:00:00.000Z",
                "version": "3.2-beta",
                "agent": "codex",
                "source_url": page_source.as_uri(),
                "page_title": "SourceLoc Smoke",
                "viewport": {"width": 1440, "height": 900},
                "changes": [
                    {
                        "type": "text_edit",
                        "selector": "h1.hero",
                        "original": "Old headline",
                        "modified": "New headline",
                        "source_anchors": source_hint["anchors"],
                        "source_hint": source_hint,
                        "locate_confidence": "high",
                    }
                ],
            }
        ]
    }
    feedback.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return feedback


def check_tokens_preview_verify() -> None:
    with tempfile.TemporaryDirectory(prefix="vfs-v32-check-") as tmp:
        project = Path(tmp)
        source = project / "index.html"
        source.write_text('<h1 class="hero">Old headline</h1><button class="cta">Join</button>', encoding="utf-8")
        (project / "styles.css").write_text(
            ":root {\n  --space-4: 16px;\n  --color-fg-muted: #667085;\n  --radius-sm: 8px;\n}\n",
            encoding="utf-8",
        )
        feedback = write_feedback(project, source)

        tokens = load_json([sys.executable, str(SCRIPTS / "scan_design_tokens.py"), str(project)])
        assert tokens["ok"] is True
        assert tokens["token_count"] >= 3
        assert (project / ".visual_feedback_studio_tokens.json").exists()
        assert any(item["name"] == "--space-4" and item["type"] == "spacing" for item in tokens["tokens"])

        inspector = load_json([sys.executable, str(SCRIPTS / "feedback_inspector.py"), str(project), "--feedback-file", str(feedback)])
        assert inspector["ok"] is True
        assert inspector["merged"]["text_edits"][0]["source_hint"]["framework"] == "react"
        assert "HeroTitle" in inspector["merged"]["text_edits"][0]["locate_summary"]

        suggestions = load_json([sys.executable, str(SCRIPTS / "suggest_style_edits.py"), str(project), "--feedback-file", str(feedback)])
        assert suggestions["ok"] is True
        assert "padding-left: var(--space-4);" in suggestions["css_preview"]
        assert "fallback padding-left: 16px;" in suggestions["css_preview"]
        assert suggestions["style_suggestions"][0]["batch_hint"]
        assert suggestions["style_suggestions"][0]["lifecycle_status"] == "needs_review"
        assert suggestions["style_suggestions"][0]["action_candidates"][0]["kind"] == "style_source_suggestion"

        before = source.read_text(encoding="utf-8")
        preview = load_json([sys.executable, str(SCRIPTS / "plan_feedback_apply.py"), str(project), "--feedback-file", str(feedback)])
        assert preview["ok"] is True
        assert preview["dry_run"] is True
        assert preview["counts"]["auto_applicable_text"] == 1
        assert len(preview["style_edits"]) == 1
        assert len(preview["annotations"]) == 1
        assert preview["text_edits"][0]["lifecycle_status"] == "planned"
        assert preview["text_edits"][0]["action_candidates"][0]["auto_applicable"] is True
        assert preview["style_edits"][0]["lifecycle_status"] == "needs_review"
        assert preview["style_edits"][0]["action_candidates"][0]["kind"] == "style_source_suggestion"
        assert preview["annotations"][0]["action_candidates"][0]["kind"] == "annotation_intent"
        assert source.read_text(encoding="utf-8") == before

        vfs_plan = load_json([sys.executable, str(SCRIPTS / "vfs.py"), "plan", str(project), "--feedback-file", str(feedback)])
        assert vfs_plan["ok"] is True
        assert vfs_plan["text_edits"][0]["lifecycle_status"] == "planned"
        vfs_tokens = load_json([sys.executable, str(SCRIPTS / "vfs.py"), "tokens", "rescan", str(project)])
        assert vfs_tokens["ok"] is True
        assert vfs_tokens["token_count"] >= 3

        verify = load_json([sys.executable, str(SCRIPTS / "verify_feedback_apply.py"), str(project), "--feedback-file", str(feedback), "--no-write"])
        assert verify["ok"] is True
        assert verify["verification_mode"] == "source_only"
        assert any(item["status"] == "not_found" and item["type"] == "text_edit" for item in verify["results"])
        assert any(item["lifecycle_status"] == "unresolved" and item["type"] == "text_edit" for item in verify["results"])

        source.write_text(source.read_text(encoding="utf-8").replace("Old headline", "New headline"), encoding="utf-8")
        verified = load_json([sys.executable, str(SCRIPTS / "verify_feedback_apply.py"), str(project), "--feedback-file", str(feedback), "--no-write"])
        assert any(item["status"] == "verified" and item["type"] == "text_edit" for item in verified["results"])
        assert any(item["lifecycle_status"] == "verified" and item["type"] == "text_edit" for item in verified["results"])

    with tempfile.TemporaryDirectory(prefix="vfs-v32-duplicate-check-") as tmp:
        project = Path(tmp)
        source = project / "index.html"
        feedback = write_feedback(project, source, duplicate=True)
        preview = load_json([sys.executable, str(SCRIPTS / "plan_feedback_apply.py"), str(project), "--feedback-file", str(feedback)])
        assert preview["counts"]["unresolved"] == 1
        assert preview["unresolved"][0]["match_count"] == 2

    with tempfile.TemporaryDirectory(prefix="vfs-v32-confidence-check-") as tmp:
        project = Path(tmp)
        source = project / "index.html"
        source.write_text('<h1 class="hero">Old headline</h1><button class="cta">Join</button>', encoding="utf-8")
        feedback = write_feedback(project, source, text_confidence="medium")
        preview = load_json([sys.executable, str(SCRIPTS / "plan_feedback_apply.py"), str(project), "--feedback-file", str(feedback)])
        assert preview["counts"]["auto_applicable_text"] == 1
        assert preview["text_edits"][0]["status"] == "auto_applicable"
        assert preview["text_edits"][0]["lifecycle_status"] == "planned"
        assert preview["text_edits"][0]["locate_confidence"] == "medium"
        assert preview["text_edits"][0]["reasons"] == ["original text appears exactly once"]
        before = source.read_text(encoding="utf-8")
        applied = load_json([sys.executable, str(SCRIPTS / "apply_text_edits.py"), str(project), "--feedback-file", str(feedback)])
        assert applied["ok"] is True
        assert applied["applied"][0]["match_count"] == 1
        assert applied["applied"][0]["lifecycle_status"] == "applied"
        assert applied["applied"][0]["reason"] == "original text appears exactly once"
        assert applied["snapshot_file"]
        assert Path(applied["snapshot_file"]).exists()
        assert applied["snapshot"]["entry_count"] == 1
        assert applied["snapshot"]["snapshot_file"] == applied["snapshot_file"]
        assert "rollback_snapshot.py" in applied["rollback_command"]
        assert str(project) in applied["rollback_command"]
        assert "New headline" in source.read_text(encoding="utf-8")
        assert source.read_text(encoding="utf-8") != before
        verified = load_json([
            sys.executable,
            str(SCRIPTS / "verify_feedback_apply.py"),
            str(project),
            "--feedback-file",
            str(feedback),
            "--snapshot-file",
            applied["snapshot_file"],
            "--no-write",
        ])
        assert verified["report_schema"] == "visual_feedback_studio.verify_report.v1"
        assert verified["summary"]["verified"] >= 1
        assert verified["summary"]["rollback_available"] is True
        assert verified["evidence_counts"]["passed"] >= 1
        assert verified["snapshot"]["entry_count"] == 1
        assert verified["rollback_command"]
        rollback_dry = load_json([
            sys.executable,
            str(SCRIPTS / "rollback_snapshot.py"),
            str(project),
            "--snapshot",
            applied["snapshot_file"],
            "--dry-run",
        ])
        assert rollback_dry["ok"] is True
        assert rollback_dry["dry_run"] is True
        assert rollback_dry["counts"]["restored"] == 1
        assert "New headline" in source.read_text(encoding="utf-8")
        rolled_back = load_json([
            sys.executable,
            str(SCRIPTS / "vfs.py"),
            "rollback",
            str(project),
            "--snapshot",
            applied["snapshot_file"],
        ])
        assert rolled_back["ok"] is True
        assert rolled_back["counts"]["restored"] == 1
        assert source.read_text(encoding="utf-8") == before
        source.write_text(source.read_text(encoding="utf-8").replace("Old headline", "Different headline"), encoding="utf-8")
        drift_rollback = load_json([
            sys.executable,
            str(SCRIPTS / "rollback_snapshot.py"),
            str(project),
            "--snapshot",
            applied["snapshot_file"],
        ])
        assert drift_rollback["ok"] is True
        assert drift_rollback["counts"]["restored"] == 0
        assert drift_rollback["counts"]["skipped"] == 1
        assert drift_rollback["skipped"][0]["reason"] == "current file differs from snapshot post-apply hash"

    with tempfile.TemporaryDirectory(prefix="vfs-v32-apply-verify-check-") as tmp:
        project = Path(tmp)
        source = project / "index.html"
        source.write_text('<h1 class="hero">Old headline</h1><button class="cta">Join</button>', encoding="utf-8")
        feedback = write_feedback(project, source, text_confidence="medium")
        report = load_json([
            sys.executable,
            str(SCRIPTS / "vfs.py"),
            "apply",
            str(project),
            "--feedback-file",
            str(feedback),
            "--verify",
        ])
        assert report["ok"] is True
        assert report["report_schema"] == "visual_feedback_studio.apply_verify_report.v1"
        assert report["verified_after_apply"] is True
        assert report["verification_summary"]["failed"] == 0
        assert report["verification_summary"]["rollback_available"] is True
        assert report["rollback_command"]
        assert report["apply"]["snapshot_file"]
        assert Path(report["apply"]["snapshot_file"]).exists()
        assert report["verify"]["report_schema"] == "visual_feedback_studio.verify_report.v1"
        assert report["verify"]["snapshot"]["entry_count"] == 1
        assert report["verify"]["evidence_counts"]["passed"] >= 1

    with tempfile.TemporaryDirectory(prefix="vfs-v32-sequence-check-") as tmp:
        project = Path(tmp)
        source = project / "index.html"
        source.write_text("<h1>Alpha</h1><p>Beta</p>", encoding="utf-8")
        feedback = project / ".visual_feedback_studio.json"
        payload = {
            "sessions": [
                {
                    "timestamp": "2026-06-04T10:00:00.000Z",
                    "version": "3.2-beta",
                    "agent": "codex",
                    "source_url": source.as_uri(),
                    "page_title": "Sequence",
                    "viewport": {"width": 1440, "height": 900},
                    "changes": [
                        {"type": "text_edit", "selector": "h1", "original": "Alpha", "modified": "Beta", "locate_confidence": "high", "source_anchors": {"testId": "title"}},
                        {"type": "text_edit", "selector": "p", "original": "Beta", "modified": "Gamma", "locate_confidence": "high", "source_anchors": {"testId": "body"}},
                    ],
                }
            ]
        }
        feedback.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        preview = load_json([sys.executable, str(SCRIPTS / "plan_feedback_apply.py"), str(project), "--feedback-file", str(feedback)])
        assert preview["ok"] is True
        assert preview["counts"]["auto_applicable_text"] == 0
        assert preview["counts"]["manual_review"] == 2
        assert all(item["lifecycle_status"] == "needs_review" for item in preview["text_edits"])
        assert all("sequence-dependent" in item["reasons"][0] for item in preview["text_edits"])
        before = source.read_text(encoding="utf-8")
        applied = load_json([sys.executable, str(SCRIPTS / "apply_text_edits.py"), str(project), "--feedback-file", str(feedback)])
        assert applied["ok"] is True
        assert not applied["applied"]
        assert len(applied["skipped"]) == 2
        assert all("sequence-dependent" in item["reason"] for item in applied["skipped"])
        assert not applied.get("snapshot_file")
        assert source.read_text(encoding="utf-8") == before

    with tempfile.TemporaryDirectory(prefix="vfs-v32-sourceloc-check-") as tmp:
        project = Path(tmp)
        src = project / "src"
        src.mkdir()
        page = project / "index.html"
        component = src / "Hero.tsx"
        page.write_text("<!doctype html><div id=\"root\"></div>", encoding="utf-8")
        component.write_text("export function Hero() {\n  return <h1>Old headline</h1>;\n}\n", encoding="utf-8")
        feedback = write_sourceloc_feedback(project, page, "src/Hero.tsx")
        preview = load_json([sys.executable, str(SCRIPTS / "plan_feedback_apply.py"), str(project), "--feedback-file", str(feedback)])
        assert preview["ok"] is True
        assert preview["counts"]["auto_applicable_text"] == 1
        assert preview["text_edits"][0]["source_resolution"] == "sourceLoc"
        assert Path(preview["text_edits"][0]["source_path"]).resolve() == component.resolve()
        assert preview["text_edits"][0]["apply_target"]["strategy"] == "source_file_unique"
        applied = load_json([sys.executable, str(SCRIPTS / "apply_text_edits.py"), str(project), "--feedback-file", str(feedback)])
        assert applied["ok"] is True
        assert applied["applied"][0]["source_resolution"] == "sourceLoc"
        assert applied["applied"][0]["lifecycle_status"] == "applied"
        assert applied["snapshot_file"]
        assert Path(applied["snapshot_file"]).exists()
        assert Path(applied["changed_paths"][0]).resolve() == component.resolve()
        assert "New headline" in component.read_text(encoding="utf-8")
        assert "New headline" not in page.read_text(encoding="utf-8")
        verified = load_json([sys.executable, str(SCRIPTS / "verify_feedback_apply.py"), str(project), "--feedback-file", str(feedback), "--no-write"])
        assert any(item["type"] == "text_edit" and item["status"] == "verified" and item["source_resolution"] == "sourceLoc" for item in verified["results"])
        component.write_text(
            "export function Hero() {\n"
            "  const label = 'fixture';\n"
            "  return <h1>New headline Old headline</h1>;\n"
            "}\n",
            encoding="utf-8",
        )
        drift = load_json([sys.executable, str(SCRIPTS / "verify_feedback_apply.py"), str(project), "--feedback-file", str(feedback), "--no-write"])
        assert any(item["type"] == "text_edit" and item["status"] == "drift" and ("original still appears" in item["reason"] or "sourceLoc line" in item["reason"]) for item in drift["results"])

    with tempfile.TemporaryDirectory(prefix="vfs-v32-sourceloc-line-check-") as tmp:
        project = Path(tmp)
        src = project / "src"
        src.mkdir()
        page = project / "index.html"
        component = src / "Hero.tsx"
        page.write_text("<!doctype html><div id=\"root\"></div>", encoding="utf-8")
        component.write_text(
            "export function Hero() {\n"
            "  return <section>\n"
            "    <h1>Old headline</h1>\n"
            "    <p>Old headline</p>\n"
            "  </section>;\n"
            "}\n",
            encoding="utf-8",
        )
        feedback = write_sourceloc_feedback(project, page, "src/Hero.tsx")
        preview = load_json([sys.executable, str(SCRIPTS / "plan_feedback_apply.py"), str(project), "--feedback-file", str(feedback)])
        assert preview["ok"] is True
        assert preview["text_edits"][0]["match_count"] == 2
        assert preview["text_edits"][0]["lifecycle_status"] == "planned"
        assert preview["text_edits"][0]["apply_target"]["strategy"] == "sourceLoc_line_unique"
        applied = load_json([sys.executable, str(SCRIPTS / "apply_text_edits.py"), str(project), "--feedback-file", str(feedback)])
        assert applied["ok"] is True
        assert applied["applied"][0]["apply_target"]["strategy"] == "sourceLoc_line_unique"
        text = component.read_text(encoding="utf-8")
        assert text.count("New headline") == 1
        assert text.count("Old headline") == 1
        second_preview = load_json([sys.executable, str(SCRIPTS / "plan_feedback_apply.py"), str(project), "--feedback-file", str(feedback)])
        assert second_preview["ok"] is True
        assert second_preview["text_edits"][0]["status"] == "manual_review"
        assert second_preview["text_edits"][0]["lifecycle_status"] == "needs_review"
        assert second_preview["text_edits"][0]["reasons"] == ["sourceLoc line already contains modified text"]
        second_apply = load_json([sys.executable, str(SCRIPTS / "apply_text_edits.py"), str(project), "--feedback-file", str(feedback)])
        assert second_apply["ok"] is True
        assert not second_apply["applied"]
        assert second_apply["skipped"][0]["reason"] == "sourceLoc line already contains modified text"
        assert component.read_text(encoding="utf-8") == text
        verified = load_json([sys.executable, str(SCRIPTS / "verify_feedback_apply.py"), str(project), "--feedback-file", str(feedback), "--no-write"])
        assert any(item["type"] == "text_edit" and item["status"] == "verified" and item["reason"] == "modified text found on sourceLoc line" for item in verified["results"])
        component.write_text(
            "export function Hero() {\n"
            "  return <section>\n"
            "    <h1>New headline Old headline</h1>\n"
            "    <p>Old headline</p>\n"
            "  </section>;\n"
            "}\n",
            encoding="utf-8",
        )
        drift = load_json([sys.executable, str(SCRIPTS / "verify_feedback_apply.py"), str(project), "--feedback-file", str(feedback), "--no-write"])
        assert any(item["type"] == "text_edit" and item["status"] == "drift" and "sourceLoc line" in item["reason"] for item in drift["results"])

    with tempfile.TemporaryDirectory(prefix="vfs-v32-style-verify-check-") as tmp:
        project = Path(tmp)
        source = project / "styles.css"
        source.write_text(
            ".other {\n  padding-left: var(--space-4);\n  border-radius: 8px;\n}\n"
            ".cta {\n  padding-left: 4px;\n  border-radius: 2px;\n}\n",
            encoding="utf-8",
        )
        feedback = write_feedback(project, source)
        verify = load_json([sys.executable, str(SCRIPTS / "verify_feedback_apply.py"), str(project), "--feedback-file", str(feedback), "--no-write"])
        style_results = [item for item in verify["results"] if item["type"] == "style_edit"]
        assert style_results and style_results[0]["status"] == "drift"
        assert "selector block" in style_results[0]["reason"]
        source.write_text(
            ".other {\n  padding-left: 4px;\n  border-radius: 2px;\n}\n"
            ".cta {\n  padding-left: var(--space-4);\n  border-radius: 8px;\n}\n",
            encoding="utf-8",
        )
        verified = load_json([sys.executable, str(SCRIPTS / "verify_feedback_apply.py"), str(project), "--feedback-file", str(feedback), "--no-write"])
        assert any(item["type"] == "style_edit" and item["status"] == "verified" for item in verified["results"])

    with tempfile.TemporaryDirectory(prefix="vfs-v32-style-root-check-") as tmp:
        base = Path(tmp)
        project = base / "project"
        project.mkdir()
        outside = base / "outside.css"
        outside.write_text(".cta {\n  padding-left: 4px;\n}\n", encoding="utf-8")
        feedback = write_feedback(project, outside)
        before = outside.read_text(encoding="utf-8")
        blocked = load_json([
            sys.executable,
            str(SCRIPTS / "suggest_style_edits.py"),
            str(project),
            "--feedback-file",
            str(feedback),
            "--apply-static",
        ])
        assert blocked["ok"] is True
        assert blocked["apply_static"]["attempted"] is False
        assert blocked["apply_static"]["unresolved"][0]["reason"] == "source file is outside project root"
        assert outside.read_text(encoding="utf-8") == before

    benchmark_script = SCRIPTS / "benchmark_source_mapping.py"
    if benchmark_script.exists():
        benchmark = load_json([sys.executable, str(benchmark_script)])
        assert benchmark["ok"] is True
        assert benchmark["case_count"] >= 7
        assert benchmark["metrics"]["auto_misapply_count"] == 0
        assert benchmark["metrics"]["auto_text_pass_rate"] == 1
        assert benchmark["metrics"]["manual_safety_pass_rate"] == 1
        assert any(case["case"] == "vite-react-dev" and case["ok"] is True for case in benchmark["cases"])
        assert any(case["case"] == "svelte-component" and case["ok"] is True for case in benchmark["cases"])
        assert any(case["case"] == "astro-production-duplicate" and case["ok"] is True for case in benchmark["cases"])


def post_json(port: int, path: str, payload: dict[str, Any], token: str = "", origin: str = "http://127.0.0.1:5173", expected_status: int = 200) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = origin
    if token:
        headers["X-VFS-Token"] = token
    req = request.Request(f"http://127.0.0.1:{port}{path}", data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=8) as resp:
            assert resp.status == expected_status
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        assert exc.code == expected_status
        raw = exc.read().decode("utf-8")
        return json.loads(raw) if raw else {"ok": False}


def get_json(port: int, path: str, origin: str = "http://127.0.0.1:5173", token: str = "", expected_status: int = 200) -> dict[str, Any]:
    headers = {"Origin": origin}
    if token:
        headers["X-VFS-Token"] = token
    req = request.Request(f"http://127.0.0.1:{port}{path}", headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=8) as resp:
            assert resp.status == expected_status
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        assert exc.code == expected_status
        raw = exc.read().decode("utf-8")
        return json.loads(raw) if raw else {"ok": False}


def read_health(host: str, port: int, timeout: float = 0.7) -> Optional[dict[str, Any]]:
    try:
        with request.urlopen(f"http://{host}:{port}/health", timeout=timeout) as resp:
            if resp.status != 200:
                return None
            payload = json.loads(resp.read().decode("utf-8"))
            return payload if isinstance(payload, dict) and payload.get("ok") else None
    except Exception:
        return None


def check_invalid_agent_fallback(port: int) -> None:
    with tempfile.TemporaryDirectory(prefix="vfs-invalid-agent-check-") as tmp:
        project = Path(tmp)
        env = {**os.environ, "VFS_HOST": "127.0.0.1", "VFS_PORT": str(port), "VFS_AGENT": "not-an-agent"}
        proc = subprocess.Popen(["node", str(SCRIPTS / "receiver.js")], cwd=str(project), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            health = None
            for _ in range(50):
                if proc.poll() is not None:
                    break
                health = read_health("127.0.0.1", port, timeout=0.3)
                if health:
                    break
                time.sleep(0.1)
            assert health and health["agent"] == "codex"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


def check_receiver(port: int) -> None:
    with tempfile.TemporaryDirectory(prefix="vfs-receiver-check-") as tmp:
        project = Path(tmp)
        source = project / "index.html"
        source.write_text('<h1 class="hero">Old headline</h1><button class="cta">Join</button>', encoding="utf-8")
        (project / "styles.css").write_text(":root { --space-4: 16px; }\n", encoding="utf-8")
        feedback = project / ".visual_feedback_studio.json"
        tokens = project / ".visual_feedback_studio_tokens.json"
        load_json([sys.executable, str(SCRIPTS / "scan_design_tokens.py"), str(project), "--output", str(tokens)])
        try:
            started = load_json([
                sys.executable,
                str(SCRIPTS / "receiver_control.py"),
                "start",
                str(project),
                "--port",
                str(port),
                "--agent",
                "claude",
                "--feedback-file",
                str(feedback),
                "--tokens-file",
                str(tokens),
            ])
            assert started["ok"] is True
            assert started["agent"] == "claude"
            assert started["health"]["token_required"] is True
            assert "token" not in started["health"]
            token = started["token"]
            assert token
            config = get_json(port, "/config", origin="chrome-extension://visualfeedback")
            assert config["token"] == token
            assert get_json(port, "/tokens", expected_status=401)["ok"] is False
            assert get_json(port, "/tokens", token=token)["token_count"] >= 1
            post_json(port, "/tokens/rescan", {}, expected_status=401)
            rescan = post_json(port, "/tokens/rescan", {}, token=token)
            assert rescan["ok"] is True
            assert rescan["token_count"] >= 1

            post_json(port, "/feedback", {
                "timestamp": "2026-06-04T10:00:00.000Z",
                "source_url": source.as_uri(),
                "changes": [{"type": "annotation", "selector": ".blocked", "note": "missing token"}],
            }, expected_status=401)
            post_json(port, "/feedback", {
                "timestamp": "2026-06-04T10:00:10.000Z",
                "source_url": source.as_uri(),
                "changes": [{"type": "annotation", "selector": ".blocked", "note": "bad origin"}],
            }, token=token, origin="https://example.com", expected_status=403)
            post_json(port, "/feedback", {
                "timestamp": "2026-06-04T10:01:00.000Z",
                "source_url": source.as_uri(),
                "changes": [{"type": "text_edit", "selector": "h1.hero", "original": "Old headline", "modified": "New headline", "locate_confidence": "high", "source_anchors": {"testId": "hero-title"}}],
            }, token=token)
            data = json.loads(feedback.read_text(encoding="utf-8"))
            assert data["sessions"][0]["version"] == "4.0-beta"
            assert data["sessions"][0]["agent"] == "claude"
            assert data["sessions"][0]["changes"][0]["status"] == "captured"
            assert data["sessions"][0]["changes"][0]["lifecycle_status"] == "captured"

            preview = post_json(port, "/apply-preview", {}, token=token)
            assert preview["ok"] is True
            assert (project / ".visual_feedback_studio_preview.json").exists()
            assert get_json(port, "/preview", expected_status=401)["ok"] is False
            assert get_json(port, "/preview", token=token)["preview"]["ok"] is True
            verify = post_json(port, "/verify", {}, token=token)
            assert verify["ok"] is True
            assert verify["verify"]["report_schema"] == "visual_feedback_studio.verify_report.v1"
            assert "evidence_counts" in verify["verify"]
            assert (project / ".visual_feedback_studio_verify.json").exists()
            assert get_json(port, "/verify-result", expected_status=401)["ok"] is False
            verify_result = get_json(port, "/verify-result", token=token)["verify"]
            assert verify_result["ok"] is True
            assert verify_result["report_schema"] == "visual_feedback_studio.verify_report.v1"
            assert "evidence_counts" in verify_result

            status = load_json([sys.executable, str(SCRIPTS / "receiver_control.py"), "status", str(project), "--port", str(port)])
            assert status["ok"] is True
            assert Path(status["health"]["last_feedback_file"]).resolve() == feedback.resolve()
            assert status["health"]["last_preview_file"]
            assert status["health"]["last_verify_file"]
            assert status["health"]["feedback_summary"]["change_count"] == 1
            assert status["health"]["preview_summary"]["exists"] is True
            assert status["health"]["verify_summary"]["exists"] is True
            assert status["health"]["verify_summary"]["report_schema"] == "visual_feedback_studio.verify_report.v1"
            assert "evidence_counts" in status["health"]["verify_summary"]
            assert "rollback_available" in status["health"]["verify_summary"]
        finally:
            stopped = run_optional([sys.executable, str(SCRIPTS / "receiver_control.py"), "stop", str(project), "--port", str(port)])
            if stopped.returncode != 0:
                try:
                    payload = json.loads(stopped.stdout)
                except json.JSONDecodeError:
                    payload = {}
                if payload.get("action") != "noop":
                    raise RuntimeError(f"receiver cleanup failed: stdout={stopped.stdout}\nstderr={stopped.stderr}")
    fallback_port = port + 1 if port < 65535 else port - 1
    check_invalid_agent_fallback(fallback_port)


def check_setup_beta_restore_and_package(port: int) -> None:
    with tempfile.TemporaryDirectory(prefix="vfs-setup-beta-check-") as tmp:
        project = Path(tmp)
        (project / "index.html").write_text("<!doctype html><h1>Setup smoke</h1>", encoding="utf-8")
        codex_stable = project / "codex-skills" / "visual-feedback-studio"
        claude_stable = project / "claude-skills" / "visual-feedback-studio"
        codex_beta = project / "codex-skills" / "visual-feedback-studio-beta"
        claude_beta = project / "claude-skills" / "visual-feedback-studio-beta"
        codex_stable.mkdir(parents=True)
        claude_stable.mkdir(parents=True)
        (codex_stable / "sentinel.txt").write_text("stable-codex", encoding="utf-8")
        (claude_stable / "sentinel.txt").write_text("stable-claude", encoding="utf-8")
        try:
            setup = load_json([
                sys.executable,
                str(SCRIPTS / "setup.py"),
                str(project),
                "--agent",
                "claude",
                "--port",
                str(port),
                "--codex-dir",
                str(codex_beta),
                "--claude-dir",
                str(claude_beta),
                "--channel",
                "beta",
            ])
            assert setup["ok"] is True
            assert setup["channel"] == "beta"
            assert setup["runtime_skill_dir"] == str(claude_beta.resolve())
            assert setup["extension"]["load_unpacked"] == str(EXTENSION.resolve())
            assert setup["extension"]["single_entry"] is True
            assert setup["extension"]["permission_model"] == "activeTab + scripting + storage + optional host permissions"
            assert setup["extension"]["store_permissions"] == ["activeTab", "scripting", "storage"]
            assert set(setup["extension"]["optional_host_permissions"]) >= {"http://*/*", "https://*/*", "file:///*"}
            assert setup["extension"]["dev_manifest_template"].endswith("manifest.dev.json")
            assert setup["first_loop"]["target"] == "5-minute first loop"
            assert setup["first_loop"]["receiver"] == "online"
            assert setup["first_loop"]["token"] == "required-and-configured"
            assert "permission_missing" in setup["failure_guidance"]
            assert setup["commands"]["rollback"].startswith("python3 ")
            assert "doctor" in setup["commands"]
            assert "apply_verify" in setup["commands"]
            assert "benchmark" in setup["commands"]
            assert setup["source_mapping_notes"]
            assert setup["token_scan"]["ok"] is True
            assert (codex_beta / "SKILL.md").exists()
            assert (claude_beta / "scripts" / "receiver_control.py").exists()
            assert (codex_stable / "sentinel.txt").read_text(encoding="utf-8") == "stable-codex"
            backups = setup["install"]["targets"][0].get("backups") or []
            assert backups and Path(backups[0]["backup"]).exists()

            restore = load_json([
                sys.executable,
                str(SCRIPTS / "setup.py"),
                "restore",
                str(project),
                "--agent",
                "codex",
                "--codex-dir",
                str(codex_stable),
                "--port",
                str(port),
            ])
            assert restore["ok"] is True
            assert (codex_stable / "sentinel.txt").read_text(encoding="utf-8") == "stable-codex"
        finally:
            stop_script = claude_beta / "scripts" / "receiver_control.py"
            if not stop_script.exists():
                stop_script = SCRIPTS / "receiver_control.py"
            run_optional([sys.executable, str(stop_script), "stop", str(project), "--port", str(port)])

        check_package_helpers(project)


def check_package_helpers(base_dir: Optional[Path] = None) -> None:
    with tempfile.TemporaryDirectory(prefix="vfs-package-check-") as tmp:
        project = base_dir or Path(tmp)
        package_zip = project / "extension.zip"
        package = load_json([sys.executable, str(SCRIPTS / "package_extension.py"), "--output", str(package_zip)])
        assert package["ok"] is True
        assert package["manifest_version"] == "4.0.0"
        assert package["permission_model"] == "store-safe optional host permissions"
        assert package_zip.exists()
        with zipfile.ZipFile(package_zip) as archive:
            names = archive.namelist()
            assert "manifest.json" in names
            assert "manifest.dev.json" not in names
            assert "vfs-helpers.js" in names
            assert "hugeicons.js" in names
            assert "inject.js" in names
            assert "popup.js" in names
            assert all(not name.startswith("._") for name in names)
            assert all("node_modules" not in name for name in names)
            assert all("examples" not in name for name in names)
            assert all("advanced-demo" not in name for name in names)
            assert all(".visual_feedback_studio" not in name for name in names)

        helper = load_json([sys.executable, str(SCRIPTS / "install_browser_helper.py")])
        assert helper["ok"] is True
        assert helper["channel"] == "beta"
        assert helper["extension_version"] == "4.0.0"
        assert helper["permission_model"] == "store-safe optional host permissions"


def main() -> int:
    args = parse_args()
    try:
        check_repository_layout()
        check_js_and_json()
        check_single_extension_entrypoint()
        warnings = check_skill_metadata(args.strict_package)
        check_public_hygiene()
        check_python_ast()
        check_extension_helpers()
        check_tokens_preview_verify()
        check_package_helpers()
        if args.receiver:
            check_receiver(args.port)
            setup_port = args.port + 2 if args.port < 65534 else args.port - 2
            check_setup_beta_restore_and_package(setup_port)
        print(json.dumps({
            "ok": True,
            "version": "4.0-beta",
            "receiver_checked": args.receiver,
            "strict_package": args.strict_package,
            "warnings": warnings,
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
