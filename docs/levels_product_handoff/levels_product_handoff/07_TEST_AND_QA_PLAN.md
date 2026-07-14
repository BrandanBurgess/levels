# LEVELS Test and QA Plan

## Backend unit tests

- unit conversion;
- Toronto local-date and DST boundaries;
- record comparison and idempotency;
- estimated 1RM bounds;
- session volume;
- progression rules;
- muscle aggregation;
- public serializers;
- exercise filters;
- measurement-type validation.

## Backend integration tests

- login success/failure/rate limit;
- write authorization;
- split/template CRUD;
- start, substitute, log, complete and edit session;
- record rebuild;
- water aggregation;
- export;
- empty-database migrations;
- idempotent seed.

## Frontend tests

- Today wake/success/empty/error;
- avatar mapping;
- journal numeric controls;
- duplicate set;
- privacy rendering;
- Growth explanations;
- split keyboard reorder;
- unit conversion;
- expired auth.

## Playwright journeys

1. Public visitor sees no edit controls.
2. Admin logs in.
3. Admin starts Upper A.
4. Admin logs incline-press sets.
5. Admin duplicates and edits a set.
6. Admin completes workout.
7. A qualifying record shows one celebration.
8. Progress shows the record.
9. Water quick-add and undo work.
10. Split edit persists after refresh.
11. Public visitor sees only configured fields.
12. Mobile at 375×812.
13. Desktop at 1440×900.
14. Simulated API cold start recovers.
15. Reduced motion suppresses animation.

## Contract

- parse/validate OpenAPI;
- generate TypeScript types;
- fail on dirty generated output;
- compare route inventory;
- validate response examples.

## Accessibility

Automated axe checks on Today, Character, Journal, Growth, Splits and Settings. Manual keyboard-only workout, screen-reader landmarks, avatar text equivalent, 200% zoom and reduced motion.

## Security checks

- rate limit;
- expired/invalid JWT;
- public mutation rejection;
- CORS denial;
- private notes absent from public responses;
- no secret in bundle;
- parameterized queries;
- production errors hide stack;
- CSV formula escaping.

## Performance

Warm dashboard API target: p95 below 500 ms for expected personal data volume. Lazy-load heavy charts/library data. Avatar remains lightweight.

Cold service: frontend explicitly tolerates wake-up delay.

## Test data

Seed at least:

- profile;
- upper/lower and PPL;
- exercise catalog;
- three completed sessions;
- one record scenario;
- one private note;
- water around UTC midnight;
- readiness pain flag.

## Commands

Implementation should provide equivalents:

```bash
make bootstrap
make dev
make lint
make typecheck
make test
make e2e
make seed
make verify
```

## Agent browser verification

The validating agent must start from clean checkout, navigate every tab, complete the admin journey, capture mobile/desktop screenshots, inspect console/network and create `VERIFICATION_REPORT.md`.

A ticket is done only when its checks pass, acceptance criteria are demonstrated and documentation is updated.
