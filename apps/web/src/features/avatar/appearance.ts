import type { components } from "@levels/api-client";

export type AvatarAppearance = components["schemas"]["AvatarSettings"];
export type AuraTier = components["schemas"]["StreakSummary"]["tier"];

export const DEFAULT_AVATAR_APPEARANCE: AvatarAppearance = {
  base_presentation: "male",
  skin_tone: "deep",
  hairstyle: "short_coils",
  hair_color: "black",
  outfit_style: "tank_and_shorts",
  outfit_palette: "violet",
  accessory: "none",
  background: "none",
  aura_style: "standard",
  aura_enabled: true,
};
