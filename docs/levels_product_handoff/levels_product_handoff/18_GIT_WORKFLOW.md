# LEVELS Git Workflow and Commit Conventions

## 1. Core rule

No product work is committed directly to `main`.

All implementation, documentation, infrastructure, tests, migrations, and fixes must be developed on a purpose-specific branch and merged through a pull request after required checks pass.

Exceptions:

- Emergency repository recovery when pull requests are impossible.
- Initial repository bootstrap before branch protection exists.

Any exception must be documented in the commit message and corrected by enabling protections immediately afterward.

## 2. Branch protection

Configure `main` with:

- Require a pull request before merging.
- Require at least one approval when a human reviewer is available.
- Require all CI status checks.
- Require branches to be up to date before merging.
- Block force pushes.
- Block branch deletion.
- Require conversation resolution.
- Prefer linear history.
- Require signed commits when practical, but do not block MVP if local signing is not configured.

Required status checks should include equivalents of:

- backend-lint
- backend-typecheck
- backend-tests
- frontend-lint
- frontend-typecheck
- frontend-tests
- openapi-contract
- build
- e2e
- secret-scan

The agent may configure branch protection through GitHub MCP when authorized. It must report any setting it could not configure automatically.

## 3. Branch naming

Use lowercase kebab-case.

Allowed prefixes:

```text
plan/
feature/
fix/
refactor/
test/
docs/
chore/
infra/
release/
hotfix/
```

Format:

```text
<prefix>/<ticket-id>-<short-description>
```

Examples:

```text
plan/lvl-001-implementation-plan
feature/lvl-201-single-owner-auth
feature/lvl-703-journal-book-ui
fix/lvl-801-pr-idempotency
test/lvl-1004-mobile-e2e
infra/lvl-1002-render-deployment
docs/lvl-000-git-workflow
```

Do not use vague branch names such as:

```text
updates
changes
work
new
final
brandan
codex
```

## 4. Feature-branch workflow

For every ticket:

1. Update local `main`.
2. Create a new branch from current `main`.
3. Implement only the ticket's bounded scope.
4. Commit coherent changes using Conventional Commits.
5. Rebase or update from `main` before opening the final pull request.
6. Push the branch.
7. Open a pull request linked to the ticket and acceptance criteria.
8. Run and pass all relevant CI checks.
9. Address review comments with additional commits.
10. Squash merge or rebase merge according to the repository's selected linear-history policy.
11. Delete the remote and local feature branch after merge.

Example commands:

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/lvl-703-journal-book-ui

# make changes
git add apps/web/src/features/journal
git commit -m "feat(journal): add mobile set entry form"

git fetch origin
git rebase origin/main
git push --set-upstream origin feature/lvl-703-journal-book-ui
```

If the branch was already pushed and then rebased:

```bash
git push --force-with-lease
```

Never use plain `--force`.

## 5. Conventional Commits

Use this structure:

```text
<type>(<scope>): <imperative summary>
```

Optional body:

```text
Explain why the change exists, important tradeoffs, migrations,
security implications, and acceptance criteria covered.
```

Optional footer:

```text
Refs: LVL-703
Closes: #42
AC: AC-JRN-01, AC-JRN-05
BREAKING CHANGE: <description>
```

### Allowed types

- `feat` — user-visible capability.
- `fix` — bug fix.
- `refactor` — internal change without intended behavior change.
- `test` — tests only.
- `docs` — documentation only.
- `chore` — maintenance.
- `build` — dependency or build-system work.
- `ci` — CI/CD configuration.
- `perf` — measurable performance improvement.
- `style` — formatting only, no behavior change.
- `revert` — revert an earlier commit.

### Recommended scopes

- `web`
- `api`
- `auth`
- `journal`
- `avatar`
- `growth`
- `records`
- `splits`
- `exercises`
- `water`
- `db`
- `openapi`
- `deploy`
- `ci`
- `docs`

### Good examples

```text
feat(journal): add duplicate set controls
feat(avatar): map upper-day targets to svg regions
fix(records): prevent duplicate achievements on retry
refactor(api): separate public and admin serializers
test(growth): cover pain-flag progression suppression
ci(pages): deploy vite build after required checks
docs(deploy): document turso token rotation
```

### Bad examples

```text
updates
fix stuff
final changes
working version
wip
changes from codex
```

## 6. Commit quality

Each commit should:

- Build or test independently when practical.
- Contain one coherent idea.
- Avoid unrelated formatting changes.
- Include migrations with the model changes that require them.
- Include tests with behavior changes.
- Avoid committing generated caches, local databases, secrets, screenshots containing secrets, or `.env` files.
- Never mix a major refactor with an unrelated feature.

Temporary `WIP` commits are allowed only on an unreviewed local branch. Before opening a pull request, squash or rewrite them into meaningful Conventional Commits.

## 7. Pull-request requirements

Every pull request must include:

- Ticket ID.
- Summary.
- Why the change is needed.
- Files or systems affected.
- Acceptance criteria covered.
- Test commands and results.
- Screenshots for visual changes.
- Migration notes.
- OpenAPI-change declaration.
- Security/privacy impact.
- Deployment impact.
- Known limitations.

Suggested template:

```markdown
## Summary

## Ticket
LVL-XXX

## Acceptance criteria
- AC-...

## Changes
- ...

## Verification
- `make lint`
- `make typecheck`
- `make test`
- `make e2e`

## Screenshots
<!-- Required for UI work -->

## Database / migration impact
None.

## OpenAPI impact
None.

## Security and privacy
No new secret or public-field exposure.

## Deployment impact
None.

## Risks / follow-ups
- ...
```

## 8. Merge strategy

Preferred:

- Squash merge each pull request into `main`.
- The squash commit title must follow Conventional Commits.
- Preserve meaningful details in the pull-request body.

Alternative:

- Rebase merge is acceptable when commits are already clean, ordered, and independently meaningful.

Avoid merge commits unless a release or repository constraint requires them.

## 9. Agent-specific rules

Coding agents must:

- Check the current branch before editing.
- Never begin feature implementation while on `main`.
- Create or switch to the ticket branch first.
- Avoid editing files owned by another active ticket unless the plan explicitly allows it.
- Commit after coherent milestones rather than one giant final commit.
- Run relevant tests before each push.
- Never rewrite shared branches without coordination.
- Use `--force-with-lease` only on the agent's own feature branch.
- Never force-push `main`.
- Open a pull request rather than merging directly when GitHub access permits.
- Include the exact commit hashes and pull-request link in the completion report.

## 10. Multi-agent coordination

The locked implementation plan must assign:

- Ticket.
- Branch name.
- Agent role.
- Allowed file paths.
- Dependencies.
- Merge order.

Agents should avoid working concurrently on the same files. When overlap is unavoidable:

1. Identify a designated owner.
2. Merge the shared foundation first.
3. Rebase dependent branches.
4. Resolve conflicts deliberately.
5. Rerun the complete affected test suite.

## 11. Release tags

Use semantic version tags after release gates pass:

```text
v0.1.0 — first functional internal MVP
v0.2.0 — public showcase MVP
v1.0.0 — stable public release
```

Create annotated tags:

```bash
git tag -a v0.1.0 -m "LEVELS internal MVP"
git push origin v0.1.0
```

Release notes should summarize features, fixes, migrations, deployment changes, and known limitations.

## 12. Verification checklist

Before merging:

- [ ] Branch follows naming convention.
- [ ] No direct work occurred on `main`.
- [ ] Commits follow Conventional Commits.
- [ ] Branch is current with `main`.
- [ ] Tests pass.
- [ ] Types pass.
- [ ] Lint passes.
- [ ] OpenAPI is synchronized.
- [ ] No secrets are committed.
- [ ] Pull-request description is complete.
- [ ] Acceptance criteria are referenced.
- [ ] Screenshots exist for UI changes.
