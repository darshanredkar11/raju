# Sanjay Chemicals — Harvey Sales Pilot

An agent-first sales workspace for Sanjay Chemicals. The home screen is a persistent chat with the sales agent, daily progress and pending approvals. The current implementation is the safe sales desk foundation; it is not yet directly wired to Harvey's upstream autonomous runtime.

## Pilot scope

- Google sign-in accepts any verified Google account; no Workspace/domain allowlist is required. Every signed-in account currently shares the same workspace, so this is intentionally open access.
- MongoDB Atlas Free is the durable record store; a bounded in-memory TTL/LRU cache reduces repeat reads.
- Persistent agent chat with recent conversation context, product-document context and daily progress.
- Chat can trigger evidence-backed market research and create email drafts that remain pending approval.
- API-backed LLM produces a sales email draft from supplied product facts and buyer context.
- Market research proposals and email drafts remain pending until an authenticated user approves them.
- Approval is tied to the exact recipient, subject and body. A changed draft cannot reuse an earlier approval.
- **No email sending code or send endpoint exists.** Approval records are not transmitted to recipients.
- API documentation is disabled in the web service; write routes require CSRF tokens and have basic rate limits.

## Run locally

Use Python 3.12 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set environment variables from .env in your shell or your IDE; never commit secrets.
uvicorn sanjay_pilot.app:app --reload
```

The app intentionally refuses to start if `SESSION_SECRET` is shorter than 32 characters. Configure MongoDB, Google OAuth and the LLM API before using the sales workflow. Run `pytest -q` for the test suite and `python scripts/check_dashboard_js.py` for dashboard JavaScript syntax validation.

## Required host environment

- `MONGODB_URI`: MongoDB Atlas connection string. Use a database user with access only to the pilot database; allowlist only the hosting egress IPs if stable, or the narrowest practical network policy.
- `MONGODB_DATABASE`: defaults to `sanjay_sales`.
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`: Google OAuth web client.
- `GOOGLE_REDIRECT_URI`: `https://YOUR-SERVICE.onrender.com/auth/google/callback`; register this exact URI in Google Cloud Console.
- Any verified Google account can sign in; no Google Workspace domain or email allowlist is required. The Google OAuth web client still must be configured. Because this is a shared workspace, every signed-in account can access its business data; use only with that access model in mind.
- `SESSION_SECRET`: at least 32 random characters. Keep it private.
- `TAVILY_API_KEY`: enables web search for market research (external search usage is subject to the provider's plan and limits).
- `LLM_API_KEY`, optionally `LLM_BASE_URL` and `LLM_MODEL`.
- `COOKIE_SECURE=true` in hosted HTTPS environments.

Never paste credentials into chat, commit `.env`, or use a MongoDB Atlas administrator credential in the application.

## Render and MongoDB

`render.yaml` is a blueprint template for a **free web-service plan only**. It does not create a database or deploy anything by itself. Connect the repository in Render and review the plan before applying it. Add secrets in Render's Environment settings. The MongoDB Atlas cluster must be created/configured separately by the owner; no paid resources are created by this repository.

Free web services can sleep when idle, and their local filesystem is not durable. MongoDB stores persistent records; the cache is deliberately ephemeral. Verify the current Render plan and MongoDB Atlas Free limits before production use.

## Product catalogue / TDS / SDS

Upload catalogue, TDS and SDS PDFs from the dashboard. The pilot limits uploads to 10 MB and 200 pages, validates the PDF signature, stores the original in MongoDB GridFS, extracts searchable text and records a SHA-256 checksum. Image-only/scanned PDFs are rejected with an OCR-required message. Select the uploaded documents when researching markets; their extracted text is supplied as source context for market research and draft generation. Do not treat a generated draft as a verified technical or regulatory statement; a human must verify specifications and claims against the original document.

## Security and operational limits

- Use HTTPS; only the Google OAuth callback should be registered.
- Any verified Google account can sign in. This is not appropriate for confidential customer data until workspace roles and access controls are added.
- Keep outbound email disabled. No SMTP/Gmail send integration is present.
- Market proposals are not automatically approved or activated as campaign targets.
- Research evidence is stored as a URL and confidence score; humans must verify source quality.
- This is a pilot scaffold, not a security certification. Review dependency alerts, access logs, backups and applicable chemical/export compliance before real customer data or outreach.
