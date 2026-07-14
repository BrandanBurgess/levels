# LEVELS Security and Privacy

## Assets and threats

Protect admin control, private notes, hidden metrics, DB credential, JWT secret, password hash and workout history.

Threats include public mutation, brute force, secret leakage, over-broad serializers, CORS abuse, token theft, injection, accidental historical mutation and CSV formula injection.

## Auth

- one admin username;
- strong password hash in backend environment;
- local no-echo hash-generation script;
- generic login failure;
- IP/username rate limit;
- short-lived bearer JWT;
- no passwords/tokens in logs;
- no registration/reset;
- logout clears client token.

Prefer memory token storage. SessionStorage is optional with documented XSS tradeoff. Never put tokens in URLs.

## Authorization

Every mutation checks backend authorization. Hidden buttons are not security.

## Public serialization

Use separate Pydantic schemas such as:

- PublicProfileResponse
- AdminProfileResponse
- PublicSessionSummary
- PublicSessionFull
- AdminSessionResponse

Never serialize full ORM models then remove private fields.

Private sessions return 404 publicly; lists/counts do not reveal them.

## CORS and CSRF

Bearer auth with exact origin allow-list. Never use wildcard credentials. Explicit tokens reduce ambient-cookie CSRF, but XSS remains important.

## XSS

- React escaping;
- no raw note HTML;
- sanitize future Markdown;
- restrictive CSP where feasible;
- audit chart/confetti dependencies.

## Database

- SQLAlchemy parameterization;
- enum allow-list for sort/filter;
- transactions for completion and records;
- foreign keys/uniqueness;
- explicit migrations.

## Idempotency

Use Idempotency-Key for set creation and session completion. Achievements have unique keys based on set/record type.

## Secrets

- ignore `.env*` except examples;
- secret scan in CI;
- no real values in docs;
- Turso token only backend;
- rotate leaked secrets immediately.

## Backups/deletion

- JSON export;
- archive referenced splits/exercises;
- confirmation for destructive actions;
- prefer soft delete/recycle period for sessions.

## Privacy defaults

- notes private;
- readiness private;
- body weight hidden;
- height configurable;
- water hidden;
- personal records public;
- completed session summaries public;
- sets configurable.

## Release checklist

- rate limit tested;
- invalid/expired JWT tested;
- public writes rejected;
- public schemas reviewed;
- CORS tested;
- secret scan passes;
- debug off;
- no production stack traces;
- dependencies audited;
- CSV formula escaping;
- private enumeration tested.
