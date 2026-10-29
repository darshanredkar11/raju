# Sanjay Chemicals — Harvey Sales Pilot

A lightweight pilot overlay for Harvey focused on qualified B2B chemical sales. Uses MongoDB Atlas for durable records, a bounded in-memory TTL cache, Google-only dashboard identity, evidence-backed market proposals, and approval-gated email drafts. External email sending is deliberately disabled in this pilot.

See the implementation and configuration files in this repository. Set secrets in the hosting provider's environment settings; never commit `.env` or credentials.
