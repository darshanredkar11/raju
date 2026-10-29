# Harvey Native Harness — Sanjay Chemicals

**This branch is not a web application.** It configures and validates the existing [upstream Harvey sales agent](https://github.com/ethanplusai/harvey), using Harvey's own runtime, dashboard, agents, persistence and approval workflow.

Start with harness/README.md and harness/COMPONENT_SELECTION.md.

## Principle

**Reuse proven components. Configure before integrating. Build only when a real requirement cannot be met.**

No second dashboard, chat UI, agent loop, memory database, email sender, or notification service by default. Harvey already provides prospecting, product-knowledge skills, native mail providers, reply handling, a persistent SQLite store, Outbox approvals, deterministic pre-send checks and a kill switch. See the upstream Harvey repository for supported behavior.

## This branch currently contains

- A reuse-first component strategy.
- Source-grounded Sanjay Chemicals product context and safety rules.
- An idempotent installer that adds those rules to Harvey's existing product_knowledge skill, with a backup.
- A read-only preflight script for an existing Harvey checkout.
- Tests for approval enforcement and safe/idempotent skill installation.
- No public service definition and no deployment step.

The old Sanjay sales-pilot prototype files are retained temporarily as reference only; they are not the target runtime and must not be deployed as a separate app.

## Apply the product context

After the native Harvey product training exists, run:

    python scripts/install_product_context.py --harvey-home /path/to/harvey

The installer only edits skills/product_knowledge.md, makes a timestamped backup, and is idempotent. It does not touch Harvey's code, config, credentials, database, or dashboard.

Then run the read-only check with the Python environment used by Harvey:

    /path/to/harvey/.venv/bin/python scripts/harvey_preflight.py --harvey-home /path/to/harvey

The preflight reads local files only. It does not start Harvey, modify config, call a model, send messages, or prove that a running runtime is connected. End-to-end verification must happen against the actual installed Harvey UI/runtime.

## Safety defaults

- Keep channels.email.require_approval: true.
- Do not activate autopilot or send real messages during setup.
- Verify product facts against official catalogues/TDS/SDS; do not invent technical or regulatory claims.
- Keep Harvey's dashboard on loopback; use its documented SSH-tunnel method for remote access.
- Do not commit secrets, local Harvey data, or customer information.
