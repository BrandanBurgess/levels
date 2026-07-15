export const AVATAR_REGION_IDS = [
  "chest_upper",
  "chest_mid",
  "chest_lower",
  "delts_front",
  "delts_side",
  "delts_rear",
  "traps",
  "upper_back",
  "lats",
  "spinal_erectors",
  "biceps",
  "brachialis",
  "triceps",
  "forearms",
  "abs",
  "obliques",
  "hip_flexors",
  "glutes",
  "abductors",
  "adductors",
  "quads",
  "hamstrings",
  "calves",
] as const;

export type AvatarRegionId = (typeof AVATAR_REGION_IDS)[number];

export const FRONT_REGION_IDS = [
  "chest_upper",
  "chest_mid",
  "chest_lower",
  "delts_front",
  "delts_side",
  "biceps",
  "brachialis",
  "forearms",
  "abs",
  "obliques",
  "hip_flexors",
  "abductors",
  "adductors",
  "quads",
  "calves",
] as const satisfies readonly AvatarRegionId[];

export const BACK_REGION_IDS = [
  "delts_rear",
  "traps",
  "upper_back",
  "lats",
  "spinal_erectors",
  "triceps",
  "forearms",
  "glutes",
  "hamstrings",
  "calves",
] as const satisfies readonly AvatarRegionId[];

export const AVATAR_REGION_LABELS: Record<AvatarRegionId, string> = {
  chest_upper: "Upper chest",
  chest_mid: "Mid chest",
  chest_lower: "Lower chest",
  delts_front: "Front deltoids",
  delts_side: "Side deltoids",
  delts_rear: "Rear deltoids",
  traps: "Trapezius",
  upper_back: "Upper back",
  lats: "Latissimus dorsi",
  spinal_erectors: "Spinal erectors",
  biceps: "Biceps",
  brachialis: "Brachialis",
  triceps: "Triceps",
  forearms: "Forearms",
  abs: "Abdominals",
  obliques: "Obliques",
  hip_flexors: "Hip flexors",
  glutes: "Glutes",
  abductors: "Hip abductors",
  adductors: "Hip adductors",
  quads: "Quadriceps",
  hamstrings: "Hamstrings",
  calves: "Calves",
};

const AVATAR_REGION_ID_SET = new Set<string>(AVATAR_REGION_IDS);

export function isAvatarRegionId(value: string): value is AvatarRegionId {
  return AVATAR_REGION_ID_SET.has(value);
}
