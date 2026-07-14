import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Avatar } from "./Avatar";

const requiredRegions = [
  "chest_upper", "chest_mid", "chest_lower", "delts_front", "delts_side", "delts_rear",
  "lats", "upper_back", "traps", "spinal_erectors", "biceps", "brachialis", "forearms",
  "triceps", "abs", "obliques", "hip_flexors", "glutes", "abductors", "quads",
  "hamstrings", "adductors", "calves",
];

describe("Avatar", () => {
  it("provides original layered front and back artwork for every seeded region", () => {
    const { container } = render(<Avatar />);

    expect(screen.getByRole("img", { name: "Front and back muscle avatar" })).toBeInTheDocument();
    expect(container.querySelectorAll('[data-view="front"]')).toHaveLength(1);
    expect(container.querySelectorAll('[data-view="back"]')).toHaveLength(1);
    expect(container.querySelectorAll('[data-layer="skin"]')).toHaveLength(2);
    expect(container.querySelectorAll('[data-layer="hair"]')).toHaveLength(2);
    expect(container.querySelectorAll('[data-layer="clothing"]')).toHaveLength(2);
    expect(container.querySelectorAll('[data-layer="outline"]')).toHaveLength(2);
    for (const region of requiredRegions) {
      expect(container.querySelector(`[data-muscle-id="${region}"]`)).not.toBeNull();
    }
  });

  it("distinguishes highlights and exposes the same targets as text", () => {
    const { container } = render(
      <Avatar targets={[
        { displayName: "Upper Chest", regionIds: ["chest_upper"], role: "primary" },
        { displayName: "Triceps", regionIds: ["triceps"], role: "secondary" },
      ]} />,
    );

    expect(container.querySelector('[data-muscle-id="chest_upper"]')).toHaveClass(
      "avatar-region--primary",
    );
    expect(container.querySelector('[data-muscle-id="triceps"]')).toHaveClass(
      "avatar-region--secondary",
    );
    expect(screen.getByRole("list", { name: "Muscles targeted today" })).toHaveTextContent(
      "Upper ChestprimaryTricepssecondary",
    );
  });
});
