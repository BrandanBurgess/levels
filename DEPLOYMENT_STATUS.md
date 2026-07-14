# Deployment Status

Status captured on 2026-07-14 for the LVL-1005 release candidate. No secret values are recorded here.

| Component | Status | Evidence / next gate |
| --- | --- | --- |
| GitHub repository | Ready | `main` is protected with the ten required CI checks, squash merge only, and no direct implementation commits. |
| GitHub Pages configuration | Configured, not deployed | Workflow-based Pages is enabled at https://brandanburgess.github.io/levels/. The deploy run for main `656bfd06d4f1eaf5ca474059553f9e7e90c455aa` correctly failed because `VITE_API_BASE_URL` is not set. |
| Render API | Service allocated; secrets and corrected build pending | Render MCP created `levels-api-brandanburgess` at https://levels-api-brandanburgess.onrender.com from exact main commit `c162a97b0a96c1877bf7341fb5faaf20afb5eca7`. Its first build proved uv must be explicitly installed; the fix is tracked in the LVL-1005 Render blocker PR. Turso and owner-auth secrets are still intentionally absent. |
| Turso database | Workflow ready, external input blocked | Turso MCP is connected and returned an empty database list. Database creation requires the account's exact group name; the production application token must then be placed directly in Render and the protected GitHub environment. |
| Production migration/seed | Not run | The protected workflow is committed, but it cannot run until the Turso database URL/token exist. Local clean-database migration, repeat seed, and invariant checks are covered in `VERIFICATION_REPORT.md`. |
| Release tag | Not created | `v0.2.0` remains gated on healthy Render, Turso, Pages, and live browser verification. Tagging an incomplete deployment would misstate release status. |

## Required external actions

1. Provide or select the Turso group name that should own `levels-production`, then create a database-scoped token without posting it in chat.
2. In the allocated Render service, apply the corrected Blueprint build command and set `/health` as the health-check path. The current Render MCP can create but cannot edit these service fields.
3. Enter `DATABASE_URL`, `TURSO_AUTH_TOKEN`, `ADMIN_PASSWORD_HASH`, and the generated `JWT_SECRET_KEY` directly in Render. Add only the Turso URL/token to the protected GitHub `production` environment for migration.
4. Run **Migrate Production Database** with the documented confirmation, verify both health endpoints, then set the non-secret repository variable `VITE_API_BASE_URL` to the Render API origin.
5. Let the Pages workflow deploy, repeat the browser suite against the live URLs, and only then create annotated tag `v0.2.0`.

## Repository evidence

- Locked planning PR: https://github.com/BrandanBurgess/levels/pull/1
- Foundation and CI PRs: https://github.com/BrandanBurgess/levels/pull/2 and https://github.com/BrandanBurgess/levels/pull/3
- Product ticket PRs: https://github.com/BrandanBurgess/levels/pull/12 through https://github.com/BrandanBurgess/levels/pull/46
- Independent-verification fixes: https://github.com/BrandanBurgess/levels/pull/47, https://github.com/BrandanBurgess/levels/pull/48, and https://github.com/BrandanBurgess/levels/pull/49
- Independent verification and release evidence: https://github.com/BrandanBurgess/levels/pull/50
- Latest successful main CI at capture time: https://github.com/BrandanBurgess/levels/actions/runs/29308798820
- Expected Pages gate failure without the API URL: https://github.com/BrandanBurgess/levels/actions/runs/29308929610

Dependabot PRs #4–#11 are automated dependency proposals and are not implementation tickets.
