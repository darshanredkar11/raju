# Harvey Native Harness — Sanjay Chemicals

This is the integration/configuration layer for the existing upstream Harvey runtime. It is not a replacement dashboard, agent framework, or hosted sales app.

- Upstream runtime and UI: https://github.com/ethanplusai/harvey
- Official company site: https://www.sanjaychemindia.com/
- Harvey owns its native dashboard, heartbeat, prospecting, writing, sending, reply handling, SQLite state, Outbox approvals, deterministic pre-send gate, bounce controls, and kill switch.
- This repository contributes a source-grounded product-context overlay and read-only readiness checks.
- No public runtime endpoint, second chat UI, second database, or separate notification service is introduced by default.

## Build and install sequence

1. Use the existing Harvey checkout; do not install a second runtime if one is already running.
2. Back up its config, .env, skills/, and data/.
3. Run native training against the official company site if the runtime is not already trained:

       harvey train https://www.sanjaychemindia.com/

4. Review the generated skills/product_knowledge.md and verify product details against current catalogue/TDS/SDS documents.
5. Apply the conservative company-level context to Harvey's existing skill:

       python scripts/install_product_context.py --harvey-home /path/to/harvey

   This creates a timestamped backup and adds a clearly marked block. Re-running it does not duplicate the block. If Harvey's native trainer later rewrites the skill, review it and reapply the overlay.
6. Run the read-only preflight using the Harvey Python environment:

       /path/to/harvey/.venv/bin/python scripts/harvey_preflight.py --harvey-home /path/to/harvey

7. In Harvey's native UI, configure a mailbox only when ready, keep email approval enabled, and test with a draft that stays in Outbox. Do not approve or send it during the smoke test.

## Reuse-first component strategy

| Capability | First choice | Add another component only when… |
|---|---|---|
| Sales agent, pipeline, email, replies, approval queue | Harvey native features | A documented requirement cannot be met by native Harvey |
| Product facts and sales instructions | Harvey trainer plus its existing product_knowledge skill | Product facts cannot be represented safely in the native skill/config model |
| Durable agent state | Harvey's native SQLite database | A concrete cross-system/team reporting requirement needs shared storage |
| Product document source of truth | Existing company catalogue/TDS/SDS files, curated into Harvey's product knowledge | Retrieval over a large changing corpus is demonstrably needed; then evaluate an existing document/RAG system before writing one |
| Research | Harvey's native Scout/discovery/profile workflow and existing research providers | Evidence from a specific source or product category is missing; add a provider adapter, not another autonomous agent by default |
| Email delivery and replies | Harvey's built-in Gmail, Microsoft 365, or SMTP/IMAP provider and Outbox | A required channel is unsupported |
| Operator notifications | Native dashboard/outbox first | A specific out-of-band alert requirement exists; evaluate an existing notification provider/service before building a service |
| Memory | Harvey's persistent state plus editable Markdown skills | Tests show a specific long-term recall requirement is unmet; benchmark existing options before adding a vector store |
| UI and authentication | Harvey's native loopback-only dashboard and token | Do not replace it. For remote access, use the documented SSH tunnel approach |

## Product-research rules

- Research product-by-product using an explicit product name/identifier; do not mix evidence across unrelated SKUs.
- Use Harvey's existing agents first. A separate agent per product is not the default.
- Separate product evidence, buyer-demand evidence, and commercial-fit hypotheses.
- Every market proposal should include the product, buyer segment, geography, evidence URL, source date where available, confidence, and open questions.
- Never infer purity, grade, CAS number, manufacturer, certifications, current stock, price, MOQ, lead time, application suitability, or export eligibility from category-level website copy.
- If exact product facts are missing, request a current catalogue/TDS/SDS instead of guessing.

## Safety defaults

- Keep email approval enabled; do not enable autopilot as part of setup.
- Do not send real outreach during installation or tests.
- Do not create paid accounts/resources or activate paid discovery providers without explicit approval.
- Keep credentials and runtime data in the Harvey installation, never in this repository.

## Preflight limitations

The script checks local files and configuration only. It does not authenticate to Harvey, inspect the running process, prove mailbox delivery, or claim end-to-end integration. Those require a smoke test on the machine where Harvey is installed.
