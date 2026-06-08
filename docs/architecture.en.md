# Architecture

[简体中文](./architecture.md)

Visual Feedback Studio connects a browser review surface with a local project workflow.

## High-Level Flow

```text
Browser page
  -> Chrome extension review UI
  -> Local receiver
  -> Structured feedback file
  -> Preview / apply / verify scripts
  -> Source edits and verification evidence
```

## Components

| Component | Role |
| --- | --- |
| Chrome extension | Starts the page review UI and captures reviewer feedback. |
| Local receiver | Writes structured feedback into the active project environment. |
| Planning scripts | Determine which feedback can be safely mapped to source. |
| Apply scripts | Apply source-proven text edits and leave unresolved items for review. |
| Verify scripts | Check whether source or browser-visible output matches the requested feedback. |
| Agent metadata | Gives AI coding agents a consistent handoff workflow. |

## Design Principles

- Local-first by default.
- Prefer proven source targets over guesswork.
- Keep unresolved feedback visible instead of hiding uncertainty.
- Separate browser capture from source modification.
- Let the current project and agent decide how to implement style and design changes.

## Public Boundary

This document describes the public workflow shape. Internal plans, private release operations, and commercial materials are intentionally not included.
