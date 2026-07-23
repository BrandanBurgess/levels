import { describe, expect, it } from "vitest";

import {
  formatRecordValue,
  formatWeight,
  weightFromKilograms,
  weightToKilograms,
  weightUnit,
} from "./units";

describe("weight units", () => {
  it("converts canonical kilograms to pounds and back without display drift", () => {
    const pounds = weightFromKilograms(60, "imperial");
    expect(pounds).toBe(132.28);
    expect(weightToKilograms(pounds, "imperial")).toBeCloseTo(60, 2);
  });

  it("keeps metric values unchanged", () => {
    expect(weightFromKilograms(60, "metric")).toBe(60);
    expect(weightToKilograms(60, "metric")).toBe(60);
    expect(weightUnit("metric")).toBe("kg");
  });

  it("formats weights and weight-derived records for the selected preference", () => {
    expect(formatWeight(60, "imperial")).toBe("132.28 lb");
    expect(formatRecordValue(100, "kg reps", "imperial")).toBe("220.46 lb reps");
    expect(formatRecordValue(8, "reps", "imperial")).toBe("8 reps");
  });
});
