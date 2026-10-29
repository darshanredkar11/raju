# Harvey Native Harness — Sanjay Chemicals

**This branch is not a web application.** It configures and validates the existing [upstream Harvey sales agent](https://github.com/ethanplusai/harvey), using Harvey's own runtime, dashboard, agents, persistence and approval workflow.

Start with harness/README.md, harness/SALES_GAP_ASSESSMENT.md, harness/SANJAY_SALES_PLAYBOOK.md and harness/COMPONENT_SELECTION.md.

## Principle

**Orchestrate proven capabilities → think like a salesperson → identify revenue-blocking gaps → find an existing solution → build only the missing piece.**

No second dashboard, chat UI, agent loop, memory database, email sender, or notification service by default. Harvey already provides prospecting, qualification, product-knowledge skills, native mail providers, reply handling, persistent SQLite state, Outbox approvals, deterministic pre-send checks and a kill switch.

## This branch contains

- A public-evidence-based sales gap assessment, with hypotheses explicitly distinguished from verified facts.
- A Sanjay Chemicals product and buyer-segment playbook.
- A source-grounded company/product context overlay and installer for Harvey's existing product_knowledge and sales_methodology skills.
- A normalized, partial-answer-friendly RFQ intake JSON Schema.
- A read-only Harvey preflight script.
- Tests for human-approval enforcement, installer safety/idempotency and RFQ schema structure.
- No public runtime endpoint and no deployment blueprint.

The old Sanjay sales-pilot prototype files are retained temporarily as reference only; they are not the target runtime and must not be deployed as a separate app.

## Apply the native Harvey overlay

After the existing Harvey checkout has its native skills, run:

    python scripts/install_product_context.py --harvey-home /path/to/harvey

The installer makes backups and adds marked blocks to existing skills; it does not replace Harvey's agents or runtime. Then run the read-only check with Harvey's Python environment:

    /path/to/harvey/.venv/bin/python scripts/harvey_preflight.py --harvey-home /path/to/harvey

The preflight reads local files only. It does not start Harvey, modify config, call a model, send messages, or prove that a running runtime is connected. End-to-end verification must happen against the actual installed Harvey UI/runtime.

## Safety defaults

- Keep channels.email.require_approval: true.
- Do not activate autopilot or send real messages during setup.
- Verify product facts against current official catalogues/TDS/SDS; do not invent technical or regulatory claims.
- Keep Harvey's dashboard on loopback; use its documented SSH-tunnel method for remote access.
- Do not commit secrets, local Harvey data, or customer information.
