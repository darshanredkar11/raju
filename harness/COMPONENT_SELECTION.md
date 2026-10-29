# Component selection notes

## Default orchestration

Use Harvey as the orchestrator and runtime. Do not add LangGraph, CrewAI, AutoGen, a second scheduler, or another agent framework unless a measurable workflow requirement cannot be met by Harvey's native agents and skills.

## Product research

Start with Harvey's existing Scout/discovery/profile pipeline and its shared `product_knowledge` skill. Run the native trainer on the official company site, then verify the output against each product catalogue/TDS/SDS. A separate research agent per SKU is not the default: product-level research can be expressed as a repeatable task using a product-specific evidence packet and explicit product identifier. Only introduce a separate workflow if the native pipeline cannot isolate product context and the tests demonstrate cross-product leakage or missing capabilities.

## Memory

Use Harvey's SQLite state for prospects, observations, conversations and workflow state. Use editable Markdown for stable sales rules and verified product facts. Do not add MongoDB, Redis, a vector database, or a memory service by default. Add retrieval infrastructure only after a representative evaluation demonstrates that the existing context window and skill files fail.

## Notifications

Harvey already supports native email providers and has an Outbox/reply workflow. Do not add Novu, Notifo, ntfy, or a custom notification microservice until a specific notification channel is required outside Harvey's native UI/email. If needed, compare an existing service's hosting cost, channel coverage, delivery guarantees, secret handling and operational burden before selecting it.

## Integration boundary

Harvey's dashboard binds to loopback and uses a bearer token. Keep it local. For remote operation use an SSH tunnel. Never build a public proxy that exposes the dashboard or put its token in a browser URL, logs, or source control.

## Required proof before adding a component

For every proposed dependency, write down:
1. The exact user-visible capability missing today.
2. A reproducible test that proves the native capability cannot meet it.
3. At least two existing candidates, including operational footprint and cost.
4. Why configuration or a small adapter is insufficient.
5. How rollback, secret rotation, retries, deduplication and monitoring work.
