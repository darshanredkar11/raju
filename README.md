# Harvey Native Harness — Sanjay Chemicals

**This branch is not a web application.** It configures and validates the existing [upstream Harvey sales agent](https://github.com/ethanplusai/harvey), using Harvey's own runtime, dashboard, agents, persistence and approval workflow.

Start with harness/README.md and harness/COMPONENT_SELECTION.md.

## Principle

**Reuse proven components. Configure before integrating. Build only when a real requirement cannot be met.**

No second dashboard, chat UI, agent loop, memory database, email sender, or notification service by default. Harvey already provides prospecting, product-knowledge skills, native mail providers, reply handling, a persistent SQLite store, Outbox approvals, deterministic pre-send checks and a kill switch. See the upstream Harvey repository for supported behavior.

## This branch currently contains

- A reuse-first component strategy.
- A read-only preflight script for an existing Harvey checkout.
- Safety tests that enforce human approval for outbound email.
- No public service definition and no deployment step.

The old Sanjay sales-pilot prototype files are retained temporarily as reference only; they are not the target runtime and must not be deployed as a separate app.

## Run the preflight

Run it with the Python environment used by the existing Harvey installation so PyYAML is available:

    /path/to/harvey/.venv/bin/python scripts/harvey_preflight.py --harvey-home /path/to/harvey

This reads local files only. It does not start Harvey, modify config, call a model, send messages, or prove that a running runtime is connected. End-to-end verification must happen against the actual installed Harvey UI/runtime.

## Safety defaults

- Keep channels.email.require_approval: true.
- Do not activate autopilot or send real messages during setup.
- Verify product facts against official catalogues/TDS/SDS; do not invent technical or regulatory claims.
- Keep Harvey's dashboard on loopback; use its documented SSH-tunnel method for remote access.
- Do not commit secrets, local Harvey data, or customer information.
