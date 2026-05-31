# Project rules — reload every session

- Control plane NEVER touches servers or keys. Deployment only via execution-plane runners.
- The Intelligence Engine (scanner, scorer, dedup, renew) is plain Python. NO LLM calls in it.
- LLM agents may only enrich, draft messages, and suggest ambiguous owners. They call signed, scoped tools only.
- Private keys never enter Jira, Teams, logs, prompts, or agent memory. Agents see cert serial/thumbprint only.
- Every state change is idempotent (key = cert_serial + renewal_window).
- Production renewal/deploy requires a Jira approval transition. Dev/test may auto-approve.
- Disable Venafi native auto-renew on any zone this platform controls.
- Secrets come from Vault/KMS at runtime. Never commit or hardcode credentials.
- Scorer and dedup logic must have 100% unit test coverage.
- Write an append-only audit event for every renewal, deploy, and close.
