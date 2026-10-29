# Harvey Native Harness — Sanjay Chemicals

This branch is the integration/configuration layer for the **existing upstream Harvey runtime**. It is not a replacement dashboard, agent framework, or hosted sales app.

- Upstream runtime and UI: https://github.com/ethanplusai/harvey
- Harvey owns its native dashboard, heartbeat, prospecting, writing, sending, reply handling, SQLite state, outbox approvals, deterministic pre-send gate, bounce controls, and kill switch.
- This repository contributes only the smallest business-specific overlay and read-only readiness checks.
- No public runtime endpoint, second chat UI, second database, or separate notification service is introduced by default.

## Architecture rule

**Reuse → configure → integrate → build only if a real requirement remains unmet.**

| Capability | First choice | Add another component only when… |
|---|---|---|
| Sales agent, pipeline, email, replies, approval queue | Harvey native features | A documented requirement cannot be met by native Harvey |
| Product facts and sales instructions | `harvey train <official-product-site>` plus Harvey's existing `skills/product_knowledge.md` | Product facts cannot be represented safely in the native skill/config model |
| Durable agent state | Harvey's native SQLite database | A concrete cross-system/team reporting requirement needs shared storage |
| Product document source of truth | Existing company catalogue/TDS/SDS files, linked or curated into Harvey's product knowledge | Retrieval over a large changing corpus is demonstrably needed; then evaluate an existing document/RAG system before writing one |
| Research | Harvey's native Scout/discovery/profile workflow and existing research providers | Evidence from a specific source or product category is missing; add a provider adapter, not another autonomous agent by default |
| Email delivery and replies | Harvey's built-in Gmail, Microsoft 365, or SMTP/IMAP provider and Outbox | A required channel is unsupported |
| Operator notifications | Native dashboard/outbox first | A specific out-of-band alert requirement exists; evaluate an existing notification provider/service before building a service |
| Memory | Harvey's persistent state plus editable Markdown skills | Tests show a specific long-term recall requirement is unmet; benchmark existing options before adding a vector store |
| UI and authentication | Harvey's native loopback-only dashboard and token | Do not replace it. For remote access, use the documented SSH tunnel approach |

## Current safety defaults

- Keep email approval enabled. Do not enable autopilot as part of setup.
- Do not send real outreach during installation or tests.
- Do not create paid accounts/resources or activate paid discovery providers without explicit approval.
- Treat supplier/manufacturer product documents as the source of truth; never invent composition, grade, certification, compliance, price, availability, or application claims.
- Keep Harvey's dashboard on loopback; access a remote runtime through an authenticated SSH tunnel, not a public reverse proxy.
- Keep credentials and runtime data in the Harvey installation, never in this repository.

## Start here

1. Locate the existing Harvey checkout/runtime; do not install a second instance if one is already running.
2. Back up its config, `.env`, `skills/`, and `data/`.
3. Run Harvey's native training against the official Sanjay Chemicals website, if available: `harvey train <official-site-url>`. Verify the generated facts against actual product catalogues/TDS/SDS.
4. Configure the native mailbox provider, but leave `channels.email.require_approval: true`.
5. Run the read-only check from this repository:

   ```bash
   python scripts/harvey_preflight.py --harvey-home /path/to/harvey
   ```

6. Start the existing native dashboard and runtime using Harvey's documented commands. Validate a test prospect and a draft; confirm the draft waits in the native Outbox. Do not approve/send it during the smoke test.

## Preflight limitations

The script checks local files and configuration only. It does not authenticate to Harvey, inspect the running process, prove mailbox delivery, or claim end-to-end integration. Those require an explicit runtime smoke test on the machine where Harvey is installed.

## Legacy pilot files

The prior web-app prototype may still exist in this branch for reference. It is **not** the target architecture and must not be deployed as a second sales UI. New work belongs in the native-runtime harness, config, validation, and integration adapters only when needed.
