# Deployment Status

Status captured on 2026-07-14 for the LVL-1005 release candidate. No secret values are recorded here.

| Component | Status | Evidence / next gate |
| --- | --- | --- |
| GitHub repository | Ready | `main` is protected with the ten required CI checks, squash merge only, and no direct implementation commits. |
| GitHub Pages | Live | https://brandanburgess.github.io/levels/ deployed from main `ab5bbd4d0bb92c2bc93c7bf6d30d3256c53c2ef6` by successful run https://github.com/BrandanBurgess/levels/actions/runs/29320166354. |
| Render API | Live | https://levels-api-brandanburgess.onrender.com uses the corrected pinned-uv build, `/health`, production secrets, and exact Pages CORS origin. Root and canonical health routes both return 200 with `database: ok`. |
| Turso database | Live and protected | `levels-production` is a default-libSQL database in group `levels`, region `aws-us-east-2`; delete protection is enabled. |
| Production migration/seed | Complete | Protected run https://github.com/BrandanBurgess/levels/actions/runs/29320025457 applied Alembic head `a91f6028df36`, seeded idempotently, and passed invariants. Independent MCP read confirmed 25 muscle groups, 98 exercises, 2 splits, and 1 profile. |
| Release tag | Ready to create | The authenticated desktop and iPhone owner journeys passed against production with clean browser/network audits and all temporary writes cleaned. Create `v0.2.0` after this evidence merges. |

## Remaining release action

Merge the final authenticated verification evidence, then create annotated tag `v0.2.0` on that exact main commit.

## Repository evidence

- Locked planning PR: https://github.com/BrandanBurgess/levels/pull/1
- Foundation and CI PRs: https://github.com/BrandanBurgess/levels/pull/2 and https://github.com/BrandanBurgess/levels/pull/3
- Product ticket PRs: https://github.com/BrandanBurgess/levels/pull/12 through https://github.com/BrandanBurgess/levels/pull/46
- Independent-verification fixes: https://github.com/BrandanBurgess/levels/pull/47, https://github.com/BrandanBurgess/levels/pull/48, and https://github.com/BrandanBurgess/levels/pull/49
- Independent verification and release evidence: https://github.com/BrandanBurgess/levels/pull/50
- Render uv bootstrap fix: https://github.com/BrandanBurgess/levels/pull/51
- Production migration and seed: https://github.com/BrandanBurgess/levels/actions/runs/29320025457
- Production Pages deployment: https://github.com/BrandanBurgess/levels/actions/runs/29320166354

Dependabot PRs #4–#11 are automated dependency proposals and are not implementation tickets.
