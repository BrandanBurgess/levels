import AxeBuilder from "@axe-core/playwright";
import { expect, test, type APIRequestContext, type Page, type TestInfo } from "@playwright/test";

const apiBaseUrl = "http://127.0.0.1:8000/api/v1";
const e2ePassword = "levels-e2e-password";

type SetLog = {
  id: string;
  set_type: "warmup" | "working" | "backoff" | "drop" | "failure";
  load_kg: number | null;
  reps: number | null;
  rir: number | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  rounds: number | null;
  bodyweight_assistance_kg: number | null;
  form_quality: number | null;
  pain_flag: boolean;
  notes: string | null;
};

type SessionExercise = {
  id: string;
  display_name: string;
  sets: SetLog[];
};

type WorkoutSession = {
  id: string;
  status: string;
  exercises: SessionExercise[];
};

async function login(page: Page): Promise<string> {
  await page.goto("/#/login");
  const responsePromise = page.waitForResponse(
    (response) => response.url().endsWith("/api/v1/auth/login") && response.request().method() === "POST",
  );
  await page.getByLabel("Username").fill("brandan");
  await page.getByLabel("Password").fill(e2ePassword);
  await page.getByRole("button", { name: "Sign in" }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const payload = (await response.json()) as { access_token: string };
  await expect(page).toHaveURL(/#\/?$/);
  await expect(page.getByRole("link", { name: "Owner sign in" })).toHaveCount(0);
  return payload.access_token;
}

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

async function openJournal(page: Page) {
  await page.getByRole("link", { name: "Journal" }).first().click();
  await expect(page.getByRole("heading", { name: "Journal", exact: true })).toBeVisible();
}

function inclineExercise(page: Page) {
  return page.locator(".journal-exercises > li").filter({
    has: page.getByRole("heading", { name: "Incline Barbell Bench Press", exact: true }),
  });
}

async function fillInclineSet(
  page: Page,
  values: { load: string; reps: string; setType: "warmup" | "working" },
) {
  const exercise = inclineExercise(page);
  await exercise.getByLabel("Weight (kg)", { exact: true }).fill(values.load);
  await exercise.getByLabel("Reps", { exact: true }).fill(values.reps);
  await exercise.getByLabel("RIR", { exact: true }).fill("2");
  await exercise.getByLabel("Form (1–5)", { exact: true }).fill("4");
  await exercise.locator(".set-entry select").selectOption(values.setType);
  await exercise.getByRole("button", { name: "Log set" }).click();
}

async function ownerSessions(request: APIRequestContext, token: string): Promise<WorkoutSession[]> {
  const response = await request.get(`${apiBaseUrl}/sessions?public_only=false`, {
    headers: authHeaders(token),
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as WorkoutSession[];
}

async function assertNoCriticalAxeViolations(page: Page) {
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(result.violations.filter((violation) => violation.impact === "critical")).toEqual([]);
}

test.describe("LEVELS handoff journeys", () => {
  test.describe.configure({ mode: "serial" });

  test("01 public visitor sees no edit controls", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Ready for Upper A/ })).toBeVisible();
    await expect(page.getByRole("link", { name: "Owner sign in" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Start Upper A/ })).toHaveCount(0);

    await page.getByRole("link", { name: "Splits" }).first().click();
    await expect(page.getByRole("heading", { name: "Splits" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Save order" })).toHaveCount(0);
    await assertNoCriticalAxeViolations(page);
  });

  test("02 admin logs in", async ({ page }) => {
    await login(page);
    await expect(page.getByRole("heading", { name: /Ready for Upper A/ })).toBeVisible();
  });

  test("03 admin starts Upper A", async ({ page }) => {
    await login(page);
    await openJournal(page);
    await page.getByRole("button", { name: /Start Upper A/ }).click();
    await expect(page.locator("#session-title")).toContainText("Upper A");
    await expect(inclineExercise(page).getByRole("button", { name: "Log set" })).toBeVisible();
  });

  test("04 admin logs incline-press sets", async ({ page }) => {
    await login(page);
    await openJournal(page);
    await fillInclineSet(page, { load: "60", reps: "8", setType: "warmup" });
    await expect(inclineExercise(page).getByRole("status")).toHaveText("Set saved remotely.");
    await expect(inclineExercise(page).locator(".logged-sets")).toContainText("60 kg × 8");
  });

  test("05 admin duplicates and edits a set", async ({ page, request }) => {
    const token = await login(page);
    await openJournal(page);
    const exercise = inclineExercise(page);
    await exercise.getByRole("button", { name: "Duplicate previous" }).click();
    await expect(exercise.getByRole("status")).toHaveText("Previous set duplicated.");

    const sessions = await ownerSessions(request, token);
    const active = sessions.find((session) => session.status === "in_progress");
    const incline = active?.exercises.find((item) => item.display_name === "Incline Barbell Bench Press");
    const duplicated = incline?.sets.at(-1);
    expect(active && incline && duplicated).toBeTruthy();
    const response = await request.patch(`${apiBaseUrl}/sets/${duplicated!.id}`, {
      headers: authHeaders(token),
      data: {
        session_exercise_id: incline!.id,
        set_type: duplicated!.set_type,
        load_kg: 62.5,
        reps: duplicated!.reps,
        rir: duplicated!.rir,
        duration_seconds: duplicated!.duration_seconds,
        distance_meters: duplicated!.distance_meters,
        rounds: duplicated!.rounds,
        bodyweight_assistance_kg: duplicated!.bodyweight_assistance_kg,
        form_quality: duplicated!.form_quality,
        pain_flag: duplicated!.pain_flag,
        notes: duplicated!.notes,
      },
    });
    expect(response.ok()).toBeTruthy();
    const edited = (await response.json()) as { set: { load_kg: number } };
    expect(edited.set.load_kg).toBe(62.5);
  });

  test("06 admin completes workout", async ({ page }) => {
    await login(page);
    await openJournal(page);
    await page.getByRole("button", { name: "Complete workout" }).click();
    await expect(page.getByRole("status")).toHaveText("Workout completed.");
    await expect(page.locator(".session-status")).toHaveText("completed");
    await page.getByRole("button", { name: "Resume workout" }).click();
    await expect(page.getByRole("status")).toHaveText("Workout resumed.");
  });

  test("07 a qualifying record shows one celebration", async ({ page }) => {
    await login(page);
    await openJournal(page);
    await fillInclineSet(page, { load: "70", reps: "10", setType: "working" });
    const celebration = page.getByRole("dialog");
    await expect(celebration).toHaveCount(1);
    await expect(celebration.getByRole("heading", { name: /personal best/i })).toBeVisible();
    await celebration.getByRole("button", { name: "Keep training" }).click();
    await expect(celebration).toHaveCount(0);
  });

  test("08 Progress shows the record", async ({ page }) => {
    await login(page);
    await page.getByRole("link", { name: "Progress" }).first().click();
    await expect(page.getByRole("heading", { name: "Personal records" })).toBeVisible();
    await expect(page.locator(".record-card").filter({ hasText: "Incline Barbell Bench Press" }).first()).toBeVisible();
  });

  test("09 water quick-add and undo work", async ({ page, request }) => {
    const token = await login(page);
    const add = await request.post(`${apiBaseUrl}/water/today`, {
      headers: { ...authHeaders(token), "Idempotency-Key": "playwright-water-add" },
      data: { amount_ml: 500 },
    });
    expect(add.status()).toBe(201);
    const added = (await add.json()) as { local_date: string; total_ml: number };
    expect(added.total_ml).toBe(500);

    const undo = await request.post(`${apiBaseUrl}/water/today/undo?date=${added.local_date}`, {
      headers: authHeaders(token),
    });
    expect(undo.ok()).toBeTruthy();
    expect(((await undo.json()) as { total_ml: number }).total_ml).toBe(0);
  });

  test("10 split edit persists after refresh", async ({ page }) => {
    await login(page);
    await page.getByRole("link", { name: "Splits" }).first().click();
    await page.getByRole("button", { name: /Move Lower A.*up/ }).click();
    await page.getByRole("button", { name: "Save order" }).click();
    await expect(page.getByRole("status")).toHaveText("Split changes saved.");
    await page.reload();
    await expect(page.locator(".split-day h3").first()).toContainText("Lower A");
  });

  test("11 public visitor sees only configured fields", async ({ page }) => {
    const dashboardResponse = page.waitForResponse((response) =>
      response.url().endsWith("/api/v1/public/dashboard"),
    );
    await page.goto("/");
    const dashboard = JSON.stringify(await (await dashboardResponse).json());
    expect(dashboard).not.toContain("notes_private");
    expect(dashboard).not.toContain("body_weight_kg\":79.4");

    await page.getByRole("link", { name: "Character" }).first().click();
    await expect(page.getByRole("definition").filter({ hasText: "Private" })).toBeVisible();
    await expect(page.getByText("5 ft 10 in")).toBeVisible();
    await page.getByRole("link", { name: "Journal" }).first().click();
    await expect(page.getByText("Private notes")).toHaveCount(0);
  });

  test("12 mobile at 375×812", async ({ page }, testInfo: TestInfo) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await login(page);
    await openJournal(page);
    const weight = inclineExercise(page).getByLabel("Weight (kg)", { exact: true });
    await expect(weight).toHaveAttribute("inputmode", "decimal");
    await expect(page.getByRole("navigation", { name: "Mobile navigation" })).toBeVisible();
    const bounds = await weight.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(375);
    await testInfo.attach("mobile-journal-375x812", {
      body: await page.screenshot({ fullPage: true }),
      contentType: "image/png",
    });
  });

  test("13 desktop at 1440×900", async ({ page }, testInfo: TestInfo) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const routes = ["/", "/#/character", "/#/journal", "/#/growth", "/#/splits", "/#/settings"];
    for (const route of routes) {
      await page.goto(route);
      await expect(page.locator("main")).toBeVisible();
      await assertNoCriticalAxeViolations(page);
    }
    await page.goto("/");
    await expect(page.locator(".desktop-sidebar")).toBeVisible();
    await testInfo.attach("desktop-today-1440x900", {
      body: await page.screenshot({ fullPage: true }),
      contentType: "image/png",
    });
  });

  test("14 simulated API cold start recovers", async ({ page }) => {
    let attempts = 0;
    await page.route("**/api/v1/public/dashboard", async (route) => {
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
    await page.goto("/");
    await expect.poll(() => attempts).toBe(3);
    await expect(page.getByRole("heading", { name: /Ready for Upper A/ })).toBeVisible();
  });

  test("15 reduced motion suppresses animation", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await login(page);
    await openJournal(page);
    await fillInclineSet(page, { load: "80", reps: "10", setType: "working" });
    const celebration = page.getByRole("dialog");
    await expect(celebration).toBeVisible();
    await expect(celebration.locator(".celebration-confetti")).toHaveCSS("display", "none");
    const duration = await celebration.evaluate((element) => getComputedStyle(element).animationDuration);
    expect(Number.parseFloat(duration)).toBeLessThanOrEqual(0.00001);
  });
});
