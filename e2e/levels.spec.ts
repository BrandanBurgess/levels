import AxeBuilder from "@axe-core/playwright";
import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";

const apiBaseUrl = "http://127.0.0.1:8000/api/v1";
const seededEmail = process.env.LEVELS_E2E_EMAIL ?? "member@levels-e2e.invalid";
const seededPassword = process.env.LEVELS_E2E_PASSWORD ?? "levels-e2e-password";
const newMember = {
  displayName: "Riley E2E",
  email: "riley@levels-e2e.invalid",
  password: "riley-e2e-password",
};

async function assertNoCriticalAxeViolations(page: Page): Promise<void> {
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(result.violations.filter((violation) => violation.impact === "critical")).toEqual([]);
}

async function assertNoHorizontalOverflow(page: Page): Promise<void> {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
}

async function login(page: Page, email = seededEmail, password = seededPassword): Promise<void> {
  await page.goto("/#/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  const responsePromise = page.waitForResponse(
    (response) => response.url().endsWith("/api/v1/auth/login") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Sign in" }).click();
  expect((await responsePromise).status()).toBe(200);
  await expect(page).toHaveURL(/#\/?$/);
  await expect(page.getByRole("heading", { name: /Ready for/ })).toBeVisible();
}

async function signOut(page: Page): Promise<void> {
  await page.locator('summary[aria-label="Account menu"]').first().click();
  const responsePromise = page.waitForResponse(
    (response) => response.url().endsWith("/api/v1/auth/logout") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Sign out" }).click();
  expect((await responsePromise).status()).toBe(204);
  await expect(page.locator('summary[aria-label="Account menu"]')).toHaveCount(0);
  await expect(page).toHaveURL(/#\/(?:login)?$/);
}

async function apiLogin(request: APIRequestContext, email: string, password: string) {
  const response = await request.post(`${apiBaseUrl}/auth/login`, { data: { email, password } });
  expect(response.status()).toBe(200);
  return (await response.json()) as { access_token: string; user: { email: string } };
}

test.describe("LEVELS v2 acceptance journeys", () => {
  test.describe.configure({ mode: "serial" });

  test("01 guest enters the fictional GET-only demo and receives a save prompt", async ({ page, request }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Progress feels better/ })).toBeVisible();
    await expect(page.getByRole("link", { name: "Try demo" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Sign in" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Create account" }).first()).toBeVisible();
    await assertNoCriticalAxeViolations(page);

    const demoResponsePromise = page.waitForResponse(
      (response) => response.url().endsWith("/api/v1/demo/bootstrap") && response.request().method() === "GET",
    );
    await page.getByRole("link", { name: "Try demo" }).click();
    const demoResponse = await demoResponsePromise;
    expect(demoResponse.status()).toBe(200);
    expect(await demoResponse.text()).not.toContain(seededEmail);
    await expect(page.getByText("Demo — changes are not saved")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Today with Alex Rivers" })).toBeVisible();

    await page.getByRole("button", { name: "Start workout" }).click();
    await expect(page.getByText("Create an account to save changes.")).toBeVisible();
    await page.getByRole("link", { name: "Character" }).click();
    await expect(page.getByRole("heading", { name: "Character" })).toBeVisible();
    await assertNoCriticalAxeViolations(page);

    expect((await request.post(`${apiBaseUrl}/demo/bootstrap`, { data: {} })).status()).toBe(405);
    expect((await request.post(`${apiBaseUrl}/today/skip`, { data: {} })).status()).toBe(401);
  });

  test("02 a new member registers, persists Appearance, signs out, and signs back in", async ({ page }) => {
    await page.goto("/#/register");
    await page.getByLabel("Display name").fill(newMember.displayName);
    await page.getByLabel("Email").fill(newMember.email);
    await page.getByLabel("Password").fill(newMember.password);
    await page.getByLabel("Preferred units").selectOption("metric");
    await page.getByLabel("Timezone").fill("America/Toronto");
    await page.getByLabel(/basic terms and privacy notice/).check();
    const registerResponse = page.waitForResponse(
      (response) => response.url().endsWith("/api/v1/auth/register") && response.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Create account" }).click();
    expect((await registerResponse).status()).toBe(201);
    await expect(page.getByRole("heading", { name: /Ready for Upper A/ })).toBeVisible();

    await page.getByRole("link", { name: "Character" }).first().click();
    await page.getByRole("tab", { name: "Appearance" }).click();
    await expect(page.getByRole("heading", { name: "Appearance" })).toBeVisible();
    await page.getByRole("radio", { name: "Female", exact: true }).check();
    await page.getByLabel("Hairstyle").selectOption("braids");
    await page.getByRole("button", { name: "Back" }).click();
    const avatarResponse = page.waitForResponse(
      (response) => response.url().endsWith("/api/v1/me/avatar") && response.request().method() === "PATCH",
    );
    await page.getByRole("button", { name: "Save appearance" }).click();
    expect((await avatarResponse).status()).toBe(200);
    await expect(page.getByRole("status")).toContainText("Appearance saved.");

    await page.getByRole("link", { name: "Today" }).first().click();
    await page.getByRole("link", { name: "Character" }).first().click();
    await page.getByRole("tab", { name: "Appearance" }).click();
    await expect(page.getByRole("radio", { name: "Female", exact: true })).toBeChecked();
    await expect(page.getByLabel("Hairstyle")).toHaveValue("braids");

    await signOut(page);
    await login(page, newMember.email, newMember.password);
    await expect(page.getByText(newMember.displayName).first()).toBeVisible();
    await signOut(page);
  });

  test("03 auth/me restores the seeded member and logout invalidates that token", async ({ request }) => {
    const auth = await apiLogin(request, seededEmail, seededPassword);
    expect(auth.user.email).toBe(seededEmail);
    const headers = { Authorization: `Bearer ${auth.access_token}` };

    const meResponse = await request.get(`${apiBaseUrl}/auth/me`, { headers });
    expect(meResponse.status()).toBe(200);
    expect((await meResponse.json()).email).toBe(seededEmail);
    expect((await request.post(`${apiBaseUrl}/auth/logout`, { headers })).status()).toBe(204);
    expect((await request.get(`${apiBaseUrl}/auth/me`, { headers })).status()).toBe(401);
  });

  test("04 member changes Lower A to Upper A, continues from there, and edits two movements", async ({ page }) => {
    await login(page);
    await expect(page.getByRole("heading", { name: "Ready for Lower A" })).toBeVisible();
    await page.getByRole("button", { name: "Change workout" }).click();
    const replacementSelect = page.getByLabel("Replacement workout");
    const upperAValue = await replacementSelect.locator("option").filter({ hasText: "Upper A" }).getAttribute("value");
    expect(upperAValue).toBeTruthy();
    await replacementSelect.selectOption(upperAValue!);
    await page.getByLabel("Continue from here").check();
    const overrideResponse = page.waitForResponse(
      (response) => response.url().endsWith("/api/v1/today/override") && response.request().method() === "PUT",
    );
    await page.getByRole("button", { name: "Apply workout change" }).click();
    expect((await overrideResponse).status()).toBe(200);
    await expect(page.getByRole("status")).toContainText("continues from there");
    await expect(page.getByRole("heading", { name: /Upper A/ }).first()).toBeVisible();

    await page.getByRole("button", { name: "Edit exercises" }).click();
    const editor = page.getByRole("list", { name: "Editable exercise plan" });
    const swapSelectors = editor.getByRole("combobox");
    expect(await swapSelectors.count()).toBeGreaterThanOrEqual(2);
    for (const index of [0, 1]) {
      const selector = swapSelectors.nth(index);
      const current = await selector.inputValue();
      const values = await selector.locator("option").evaluateAll((options) =>
        options.map((option) => (option as HTMLOptionElement).value),
      );
      const replacement = values.find((value) => value !== current);
      expect(replacement).toBeTruthy();
      await selector.selectOption(replacement!);
    }
    await page.getByRole("button", { name: /Move .* down/ }).first().click();
    const exercisesResponse = page.waitForResponse(
      (response) => response.url().endsWith("/api/v1/today/exercises") && response.request().method() === "PUT",
    );
    await page.getByRole("button", { name: "Save for today only" }).click();
    const exercisePlanResponse = await exercisesResponse;
    expect(exercisePlanResponse.status(), await exercisePlanResponse.text()).toBe(200);
    await expect(page.getByRole("status").filter({ hasText: "saved for today only" })).toBeVisible();
    await assertNoCriticalAxeViolations(page);
  });

  test("05 member starts and completes the adjusted workout and keeps it after a fresh sign-in", async ({ page }) => {
    await login(page);
    await page.getByRole("link", { name: "Journal" }).first().click();
    await expect(page.getByRole("heading", { name: "Journal" })).toBeVisible();
    const startButton = page.getByRole("button", { name: /Start Upper A/ });
    await expect(startButton).toBeVisible();
    const startResponse = page.waitForResponse(
      (response) => response.url().endsWith("/api/v1/sessions") && response.request().method() === "POST",
    );
    await startButton.click();
    expect((await startResponse).status()).toBe(201);
    await expect(page.locator("#session-title")).toContainText("Upper A");

    const completeResponse = page.waitForResponse(
      (response) => /\/api\/v1\/sessions\/[^/]+$/.test(response.url()) && response.request().method() === "PATCH",
    );
    await page.getByRole("button", { name: "Complete workout" }).click();
    expect((await completeResponse).status()).toBe(200);
    await expect(page.getByRole("status")).toContainText("Workout completed.");
    await expect(page.locator(".session-status")).toHaveText("completed");

    await signOut(page);
    await login(page);
    await page.getByRole("link", { name: "Journal" }).first().click();
    await expect(page.getByRole("navigation", { name: "Workout sessions" })).toContainText("Upper A");
    await expect(page.getByRole("navigation", { name: "Workout sessions" })).toContainText("completed");
  });

  test("06 Character exposes Skip and keep-next for the new member", async ({ page }) => {
    await login(page, newMember.email, newMember.password);
    await page.getByRole("link", { name: "Character" }).first().click();
    await expect(page.getByRole("heading", { name: newMember.displayName })).toBeVisible();
    await page.getByLabel("After skipping").selectOption("keep");
    const skipResponse = page.waitForResponse(
      (response) => response.url().endsWith("/api/v1/today/skip") && response.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Skip today" }).click();
    expect((await skipResponse).status()).toBe(200);
    await expect(page.getByText("Today skipped. Your plan and streak were updated.")).toBeVisible();
  });

  test("07 landing, demo, member Today, and Appearance have no critical a11y or viewport overflow", async ({ page }) => {
    const browserErrors: string[] = [];
    const failedRequests: string[] = [];
    const serverErrors: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error") browserErrors.push(message.text());
    });
    page.on("pageerror", (error) => browserErrors.push(error.message));
    page.on("requestfailed", (request) => {
      failedRequests.push(`${request.method()} ${request.url()}: ${request.failure()?.errorText ?? "unknown"}`);
    });
    page.on("response", (response) => {
      if (response.status() >= 500) serverErrors.push(`${response.status()} ${response.url()}`);
    });

    for (const viewport of [
      { width: 375, height: 812 },
      { width: 390, height: 844 },
      { width: 1440, height: 900 },
    ]) {
      await page.setViewportSize(viewport);
      await page.goto("/");
      await expect(page.getByRole("link", { name: "Try demo" })).toBeVisible();
      await assertNoHorizontalOverflow(page);
      await assertNoCriticalAxeViolations(page);
      await page.goto("/#/demo");
      await expect(page.getByRole("heading", { name: "Today with Alex Rivers" })).toBeVisible();
      await assertNoHorizontalOverflow(page);
    }

    await login(page);
    await assertNoHorizontalOverflow(page);
    await page.getByRole("link", { name: "Character" }).first().click();
    await page.getByRole("tab", { name: "Appearance" }).click();
    await expect(page.getByRole("heading", { name: "Appearance" })).toBeVisible();
    await assertNoHorizontalOverflow(page);
    await assertNoCriticalAxeViolations(page);
    expect(browserErrors).toEqual([]);
    expect(failedRequests).toEqual([]);
    expect(serverErrors).toEqual([]);
  });

  test("08 streak aura becomes static when reduced motion is requested", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await login(page);
    await page.getByRole("link", { name: "Character" }).first().click();
    await page.getByRole("tab", { name: "Appearance" }).click();
    const aura = page.locator(".avatar-aura__glow").first();
    await expect(aura).toBeVisible();
    await expect(aura).toHaveCSS("animation-name", "none");
    await assertNoHorizontalOverflow(page);
  });

  test("09 demo GET retries through a simulated API cold start", async ({ page }) => {
    let attempts = 0;
    await page.route("**/api/v1/demo/bootstrap", async (route) => {
      attempts += 1;
      if (attempts <= 2) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ error: { code: "WAKING", message: "Service is waking" } }),
        });
      } else {
        await route.continue();
      }
    });
    await page.goto("/#/demo");
    await expect.poll(() => attempts).toBe(3);
    await expect(page.getByRole("heading", { name: "Today with Alex Rivers" })).toBeVisible();
  });
});
