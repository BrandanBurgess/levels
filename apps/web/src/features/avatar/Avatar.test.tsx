import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Avatar } from "./Avatar";
import { DEFAULT_AVATAR_APPEARANCE } from "./appearance";
import { AVATAR_REGION_IDS } from "./regions";

function renderedRegionIds(container: HTMLElement) {
  return new Set(
    Array.from(container.querySelectorAll<SVGElement>("[data-region-id]"))
      .map((element) => element.dataset.regionId)
      .filter((value): value is string => Boolean(value)),
  );
}

describe("Avatar", () => {
  it.each(["male", "female"] as const)(
    "renders original layered %s front/back artwork with the canonical 23-region contract",
    (basePresentation) => {
      const { container } = render(
        <Avatar
          appearance={{ ...DEFAULT_AVATAR_APPEARANCE, base_presentation: basePresentation }}
        />,
      );

      expect(
        screen.getByRole("img", { name: `Front and back ${basePresentation} muscle avatar` }),
      ).toBeInTheDocument();
      expect(container.querySelectorAll('[data-view="front"]')).toHaveLength(1);
      expect(container.querySelectorAll('[data-view="back"]')).toHaveLength(1);
      expect(container.querySelectorAll(`[data-base="${basePresentation}"]`)).toHaveLength(2);
      expect(container.querySelectorAll('[data-layer="hair"]')).toHaveLength(2);
      expect(container.querySelectorAll('[data-layer="outfit"]')).toHaveLength(2);
      expect(renderedRegionIds(container)).toEqual(new Set(AVATAR_REGION_IDS));
      expect(container.querySelectorAll("[data-region-id] path:not([data-region-id])")).toHaveLength(0);
    },
  );

  it("uses non-color cues, focusable regions, a legend, and equivalent target text", () => {
    const { container } = render(
      <Avatar
        targets={[
          { displayName: "Upper Chest", regionIds: ["chest_upper"], role: "primary" },
          { displayName: "Triceps", regionIds: ["triceps"], role: "secondary" },
          { displayName: "Core stability", regionIds: ["abs"], role: "stabilizer" },
        ]}
        view="front"
      />,
    );

    expect(container.querySelector('[data-region-id="chest_upper"]')).toHaveAttribute(
      "data-highlight-cue",
      "solid-bold",
    );
    expect(container.querySelector('[data-region-id="triceps"]')).toBeNull();
    expect(container.querySelector('[data-region-id="abs"]')).toHaveAttribute(
      "data-highlight-cue",
      "dotted",
    );
    expect(screen.getByRole("list", { name: "Muscle highlight legend" })).toHaveTextContent(
      "Primary · bold border and glowSecondary · dashed borderStabilizer · dotted outline",
    );
    expect(screen.getByRole("list", { name: "Muscles targeted today" })).toHaveTextContent(
      "Upper ChestprimaryTricepssecondaryCore stabilitystabilizer",
    );

    fireEvent.focus(screen.getByRole("button", { name: "Upper chest: primary target" }));
    expect(screen.getByRole("status")).toHaveTextContent("Upper chest · primary · Upper Chest");
  });

  it("renders the server tier as a static aura when reduced motion is requested and honors disable", () => {
    const appearance = { ...DEFAULT_AVATAR_APPEARANCE, aura_enabled: true, aura_style: "rings" as const };
    const { container, rerender } = render(
      <Avatar appearance={appearance} auraTier="energized" reducedMotion view="front" />,
    );

    expect(container.querySelector('[data-aura-tier="energized"]')).not.toBeNull();
    expect(container.querySelector('[data-reduced-motion="true"]')).not.toBeNull();

    rerender(
      <Avatar
        appearance={{ ...appearance, aura_enabled: false }}
        auraTier="legendary"
        view="front"
      />,
    );
    expect(container.querySelector("[data-aura-tier]")).toBeNull();
  });
});
