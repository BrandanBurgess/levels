export type UnitPreference = "imperial" | "metric";

export const POUNDS_PER_KILOGRAM = 2.2046226218487757;

function rounded(value: number, maximumFractionDigits: number) {
  return Number(value.toFixed(maximumFractionDigits));
}

export function weightUnit(units: UnitPreference) {
  return units === "imperial" ? "lb" : "kg";
}

export function weightFromKilograms(
  kilograms: number,
  units: UnitPreference,
  maximumFractionDigits = 2,
) {
  return rounded(
    units === "imperial" ? kilograms * POUNDS_PER_KILOGRAM : kilograms,
    maximumFractionDigits,
  );
}

export function weightToKilograms(
  weight: number,
  units: UnitPreference,
  maximumFractionDigits = 6,
) {
  return rounded(
    units === "imperial" ? weight / POUNDS_PER_KILOGRAM : weight,
    maximumFractionDigits,
  );
}

export function formatWeight(
  kilograms: number,
  units: UnitPreference,
  maximumFractionDigits = 2,
) {
  const value = weightFromKilograms(kilograms, units, maximumFractionDigits);
  return `${value.toLocaleString(undefined, { maximumFractionDigits })} ${weightUnit(units)}`;
}

export function formatRecordValue(
  value: number,
  unit: string,
  units: UnitPreference,
) {
  if (units !== "imperial" || !unit.startsWith("kg")) {
    return `${rounded(value, 2).toLocaleString()} ${unit}`;
  }
  const convertedUnit = unit.replace(/^kg/, "lb");
  const convertedValue = weightFromKilograms(value, units, 2);
  return `${convertedValue.toLocaleString()} ${convertedUnit}`;
}
