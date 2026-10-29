# Render Harvey POC — free-tier feasibility and safe test plan

## Decision

Do not deploy the upstream Harvey dashboard directly as a public Render web service, even for a pilot. Harvey intentionally binds its dashboard to 127.0.0.1, rejects non-loopback Host headers, requires a bearer token for API routes, and documents SSH tunnelling for remote Linux access. A naive change to bind 0.0.0.0 or to bypass Host validation would weaken the upstream security boundary.

The existing Render free web service is the older Sanjay Chemicals pilot. Do not overwrite or repurpose it for Harvey.

## What the free tier can prove

Render's official free-web-service documentation says:
- services spin down after 15 minutes without inbound traffic;
- local filesystem changes are lost on spin-down, restart and redeploy;
- persistent disks and SSH/shell access are unavailable on free web services;
- free web services may restart at any time.

Therefore, a free-tier deployment cannot prove durable Harvey SQLite/config/skills, CLI login persistence, restart recovery, or the documented private dashboard workflow.

A free-tier experiment is limited to non-production build/boot feasibility and must not be represented as a connected or operational Harvey instance.

## Safe POC gates

### Gate A — free, no service mutation
1. Review the upstream Dockerfile and Compose configuration.
2. Validate upstream security assumptions and Render's port/host model.
3. Run repository tests and static checks in CI where possible.
4. Keep the existing Sanjay pilot unchanged.
5. Do not add model, mailbox, or customer secrets to a free test service.

### Gate B — if a free deployment is attempted
Only create a separate service from an isolated POC branch after confirming that:
- it doesn't replace the existing Sanjay pilot;
- it does not expose the Harvey dashboard publicly or disable the loopback/Host/token checks;
- the service exposes only a non-sensitive liveness/readiness result;
- all data is disposable and contains no credentials or customer data;
- success is described only as build/boot feasibility, not runtime connectivity.

If these conditions cannot be met with the supported upstream deployment, skip the free deployment rather than creating an insecure workaround.

### Gate C — paid Render, after user approval
1. Create a separate paid service with persistent storage if needed.
2. Implement a documented private-access pattern that preserves dashboard security (prefer private networking / authenticated access supported by the platform; do not assume SSH access is available until verified).
3. Provision model-provider login and data paths securely.
4. Run the Sanjay overlay installer and preflight.
5. Test model response, product-specific research evidence, draft generation, Outbox human approval, persistence across restart/redeploy and access-control behavior.
6. Leave all outbound sending disabled until the user explicitly approves a separate send test.

## Definition of done

Only mark Harvey connected after the real runtime can authenticate to its supported model provider, use the Sanjay product context, produce evidence-backed research and a draft in its native Outbox, retain state across restart, and keep the dashboard protected. A successful image build or health endpoint is not sufficient.

## Sources

- Render free service limitations: https://render.com/docs/free
- Harvey upstream deployment/security instructions: https://github.com/ethanplusai/harvey
- Harvey native dashboard authentication: https://github.com/ethanplusai/harvey/blob/main/harvey/dashboard_auth.py
