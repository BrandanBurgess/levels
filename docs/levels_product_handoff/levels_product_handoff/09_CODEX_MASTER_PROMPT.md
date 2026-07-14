# Master Prompt for Codex

You are the principal engineer implementing **LEVELS**, a public workout showcase and single-owner workout tracker.

Read every file in the handoff folder, including `18_GIT_WORKFLOW.md`, and inspect the repository.

## First: plan, then continue implementation

Create `IMPLEMENTATION_PLAN_LOCKED.md` with:

- architecture confirmation;
- conflict resolutions;
- repository structure;
- dependency graph;
- phased tickets and file ownership;
- an assigned feature/fix branch name for every ticket;
- tests/deployment gates;
- external human steps;
- risks;
- exact commands.

Conflict precedence:

1. OpenAPI
2. data model and SQL schema
3. acceptance criteria
4. PRD
5. other docs

After writing the plan, continue implementing end to end. Do not stop at planning.

## Mandatory Git workflow

Before editing product code:

1. Confirm the current branch.
2. Update local `main`.
3. Create the ticket branch assigned in `IMPLEMENTATION_PLAN_LOCKED.md`.
4. Never implement a feature, fix, migration, test suite, documentation change, or infrastructure change directly on `main`.

Follow `18_GIT_WORKFLOW.md`.

Required behavior:

- One purpose-specific branch per ticket.
- Branch names such as `feature/lvl-703-journal-book-ui`.
- Conventional Commits such as `feat(journal): add duplicate set controls`.
- Coherent commits throughout implementation rather than one giant final commit.
- A pull request for every ticket.
- Ticket IDs and acceptance criteria in pull-request descriptions.
- Relevant CI checks passing before merge.
- Squash merge by default with a Conventional Commit title.
- No force push to `main`.
- `--force-with-lease` only on an agent-owned feature branch.
- Delete merged feature branches.
- Report branch name, commit hashes, and pull-request URL.

Use GitHub MCP to configure protected `main` when authorized. Require pull requests and status checks, block force pushes, prefer linear history, and enable automatic deletion of merged branches. Record any repository setting that still requires Brandan to change manually.

## Locked product constraints

- public read without account;
- only Brandan edits;
- no registration;
- React + TypeScript + Vite;
- Flask backend;
- Turso/libSQL production, SQLite-compatible local;
- GitHub Pages frontend;
- Render backend;
- original layered SVG avatar;
- black/multi-purple theme;
- paper/book journal;
- active upper/lower and inactive PPL;
- no deadlift variants in seeds or automatic suggestions;
- deterministic conservative Growth;
- strict typing;
- local browser verification.

## Order

1. foundation and CI;
2. models/migrations/seed;
3. auth and APIs;
4. frontend shell;
5. Today/Character;
6. Journal/session lifecycle;
7. records;
8. Growth;
9. Splits/Library;
10. Progress/export;
11. deployment;
12. QA/fixes.

Delegate bounded tickets to cheaper coding agents when available. Keep OpenAPI and generated client synchronized.

## Quality

- no core placeholders;
- no secrets committed;
- no unchecked TypeScript `any`;
- typed SQLAlchemy and Pydantic;
- public allow-list serializers;
- rate-limited login;
- PR idempotency tests;
- mobile numeric entry;
- responsive 375×812 and 1440×900;
- reduced motion;
- friendly cold-start state;
- historical sessions independent of templates;
- navigate app locally.

## Required commands

Create/run equivalents:

```bash
make bootstrap
make lint
make typecheck
make test
make e2e
make verify
```

Migrate and seed a clean database. Complete the full admin browser journey.

## Required final outputs

- working app;
- feature-branch and pull-request history following `18_GIT_WORKFLOW.md`;
- passing tests;
- Pages workflow;
- Render configuration;
- Turso guide;
- `.env.example`;
- seeds;
- screenshots;
- `VERIFICATION_REPORT.md`;
- `DECISIONS_IMPLEMENTED.md`;
- root README;
- concise human-only setup steps.

Do not claim completion if a test, type check, build, migration or browser journey fails.
