# Single-server deployment plan — Oracle Cloud + native Harvey

## Decision

Use one Oracle Cloud Infrastructure (OCI) Ubuntu ARM64 VM as the only application server for the pilot. Run the upstream Harvey runtime and native dashboard from its official repository. Keep the existing Render pilot out of the active workflow; do not add another dashboard, API server, MongoDB, queue, or agent framework unless a verified requirement needs one.

This is a deployment runbook, not a claim that Harvey is already installed or connected.

## Target shape

- One OCI VM in the tenancy's home region, using an Always Free-eligible Ampere A1 shape if capacity is available.
- Ubuntu ARM64, Docker Engine + Compose plugin.
- Official upstream checkout: https://github.com/ethanplusai/harvey
- Sanjay Chemicals overlay from https://github.com/darshanredkar11/raju, branch `harvey-native-harness`.
- Harvey's native skills, SQLite state, dashboard and Outbox remain on that VM.
- Dashboard binds only to 127.0.0.1:5555. Access from the operator's computer using SSH local port forwarding; do not open port 5555 to the Internet.
- Use the model provider supported by upstream Harvey and already available to the owner: Claude Code login or the supported Codex CLI route. This is subscription-backed CLI auth, not an arbitrary LLM API key.

## Phase 0 — OCI account and VM

1. Sign in to the existing OCI account (do not create duplicate free accounts).
2. In the tenancy's home region, check Always Free limits and Ampere capacity.
3. Create one Ubuntu ARM64 Ampere A1 VM. Start within Always Free limits if offered; do not select paid shapes or services without explicit approval.
4. Use SSH public-key authentication. Keep the private key on the operator's device.
5. Configure network ingress to allow SSH (TCP 22) only from the operator's current public IP where practical. Do not add public ingress for TCP 5555.
6. Record the public IP and instance shape privately. Never commit SSH keys, cloud credentials, model login files, or tokens.

If A1 capacity is unavailable, retry later or assess another home-region option. Do not silently switch to a billable resource.

## Phase 1 — baseline host security

Connect over SSH, then:
- Apply Ubuntu security updates.
- Create/use a non-root operator account with sudo.
- Enable SSH key-only access; disable password SSH after verifying key login works.
- Configure a host firewall: default deny inbound; permit SSH from the operator IP if possible.
- Install Docker Engine and the Compose plugin from Docker's official Ubuntu instructions.
- Ensure the operator account can run Docker safely; Docker group membership is effectively root-equivalent.
- Check free disk, memory and CPU before proceeding.

## Phase 2 — install the upstream runtime

Use the upstream Harvey README as the source of truth. Its Linux Docker Compose path is:
1. Clone https://github.com/ethanplusai/harvey into a dedicated directory such as `/opt/harvey` (owned by the non-root operator; do not run the app as root).
2. Create `.env` from `.env.example` only if it does not already exist.
3. Export `HARVEY_UID` and `HARVEY_GID` for the operator.
4. Authenticate the selected supported CLI on the host before starting the container. Claude requires a working `claude login`; the upstream Docker image does not include Codex, so do not choose Codex for this Compose path unless the upstream installation instructions have been followed for a supported host install.
5. Run the upstream `docker compose build`, then `docker compose run --rm harvey setup`.
6. Start with `docker compose up -d` and inspect logs. Do not enable autonomous sending.

Upstream reference: https://github.com/ethanplusai/harvey/blob/main/README.md

## Phase 3 — apply the Sanjay Chemicals overlay

1. Clone this repository in a separate work directory, branch `harvey-native-harness`.
2. Back up Harvey's `harvey.local.yaml` or `harvey.yaml`, `.env`, `skills/`, and `data/` to a restricted backup location. Do not upload these files to GitHub.
3. Review the current official Sanjay Chemicals product catalogue and current TDS/SDS documents. Treat the public website as discovery material, not proof of current stock, price, lead time, grade, CAS, certification or export eligibility.
4. Run the overlay installer from this repository against the existing Harvey checkout:
   `python scripts/install_product_context.py --harvey-home /opt/harvey`
   The script backs up and appends marked context to existing native skills; it must not replace the native agent or runtime.
5. Run the read-only preflight using Harvey's Python environment as documented in `harness/README.md`. Resolve errors and review warnings.
6. Review the final native config and skill diffs before starting/restarting Harvey.

## Phase 4 — private UI and runtime smoke test

From the operator's local computer, open an SSH tunnel:
`ssh -N -L 5555:127.0.0.1:5555 <operator>@<VM_PUBLIC_IP>`

Then open `http://127.0.0.1:5555` using the private unlock link printed by Harvey. Never share the unlock token.

Smoke test in this order:
1. Dashboard loads over the SSH tunnel; direct public access to port 5555 fails.
2. Harvey reports its selected model provider as authenticated and can complete a harmless test prompt.
3. Company/product context is visible in the native skills/config.
4. Run a single narrow product × buyer segment × geography research task and inspect evidence URLs.
5. Generate one email draft to a controlled test address or placeholder; verify it remains in Outbox.
6. Verify approval is required and sending is paused/disabled. Do not send any real message in the smoke test.
7. Restart the service and confirm skills, config and SQLite state persist.
8. Confirm logs do not print credentials, session tokens, or full customer data.

## Phase 5 — operational hardening before real sales use

- Set and test a backup schedule for `data/`, `harvey.local.yaml`, `.env`, and customized `skills/`; encrypt backups and restrict access.
- Test restore, not just backup creation.
- Set cloud budget alerts and monitor VM CPU, memory, disk, uptime and Harvey logs.
- Rotate any credentials that were ever exposed.
- Keep human approval enabled for all outbound messages; do not activate autopilot as part of installation.
- Use a dedicated, authorized sending mailbox only after its ownership, provider setup, deliverability and company approval are confirmed.
- Verify product claims against current approved TDS/SDS/catalogue; require human confirmation for quotes, stock, lead time, price and technical suitability.
- Check upstream license, provider subscription terms, and usage limits before operational use.
- Define a rollback: stop Compose, restore the last known-good checkout/config/skills/data backup, and verify the native dashboard is still private.

## Definition of done

The runtime is considered connected only after the real VM has passed the private-dashboard, model-authentication, product-context, research-evidence, draft-to-Outbox, restart-persistence and public-port-is-closed checks. A successful cloud VM creation or a green static preflight alone does not count as runtime connectivity.

## Explicitly not included yet

- No real outbound campaigns.
- No public reverse proxy or public Harvey dashboard.
- No second custom UI/API or MongoDB.
- No paid OCI resources without approval.
- No claim of successful installation until the runtime smoke tests above have actually run.
