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

  it("renders long curls as a distinct textured style on a female front and back avatar", () => {
    const { container } = render(
      <Avatar
        appearance={{
          ...DEFAULT_AVATAR_APPEARANCE,
          base_presentation: "female",
          hairstyle: "long_curls",
        }}
      />,
    );

    expect(container.querySelectorAll('.avatar__figure--female[data-hairstyle="long_curls"]')).toHaveLength(2);
    expect(container.querySelectorAll('[data-hair-layer="rear"][data-hairstyle="long_curls"]')).toHaveLength(2);
    expect(container.querySelectorAll('[data-hair-layer="front"][data-hairstyle="long_curls"]')).toHaveLength(2);
    expect(container.querySelectorAll('[data-hair-texture="long-curls"]')).toHaveLength(2);
  });

  it("renders short locs and a view-aware cap on a male avatar", () => {
    const { container } = render(
      <Avatar
        appearance={{
          ...DEFAULT_AVATAR_APPEARANCE,
          accessory: "cap",
          base_presentation: "male",
          hairstyle: "short_locs",
        }}
      />,
    );

    expect(container.querySelectorAll('[data-base="male"]')).toHaveLength(2);
    expect(container.querySelectorAll('[data-hair-texture="short-locs"]')).toHaveLength(2);
    expect(container.querySelectorAll('[data-accessory="cap"]')).toHaveLength(2);
    const frontBill = container.querySelector('[data-view="front"] .avatar__accessory-cap path:last-child');
    const backBand = container.querySelector('[data-view="back"] .avatar__accessory-cap path:last-child');
    expect(frontBill).not.toBeNull();
    expect(backBand).not.toBeNull();
    expect(frontBill?.getAttribute("d")).not.toBe(backBand?.getAttribute("d"));
  });

  it("keeps long locs and braids visually and structurally distinct", () => {
    const { container, rerender } = render(
      <Avatar appearance={{ ...DEFAULT_AVATAR_APPEARANCE, hairstyle: "locs" }} view="back" />,
    );

    const locs = container.querySelector('[data-view="back"] [data-hair-texture="locs"]');
    expect(locs).not.toBeNull();
    expect(locs).toHaveClass("avatar__hair-strands--locs");
    const locsMarkup = locs?.innerHTML;

    rerender(
      <Avatar appearance={{ ...DEFAULT_AVATAR_APPEARANCE, hairstyle: "braids" }} view="back" />,
    );
    const braids = container.querySelector('[data-view="back"] [data-hair-texture="braids"]');
    expect(braids).not.toBeNull();
    expect(braids).toHaveClass("avatar__hair-strands--braids");
    expect(braids?.innerHTML).not.toBe(locsMarkup);
    expect(braids?.querySelectorAll("circle")).toHaveLength(6);
  });

  it.each([
    ["female", "bob"],
    ["female", "long_curls"],
    ["male", "short_locs"],
  ] as const)("keeps the %s %s face between rear hair and the front hairline", (basePresentation, hairstyle) => {
    const { container } = render(
      <Avatar
        appearance={{
          ...DEFAULT_AVATAR_APPEARANCE,
          base_presentation: basePresentation,
          hairstyle,
        }}
        view="front"
      />,
    );

    const figure = container.querySelector(`[data-view="front"] .avatar__figure[data-hairstyle="${hairstyle}"]`);
    const childLayers = Array.from(figure?.children ?? []).map((element) => [
      element.getAttribute("data-layer"),
      element.getAttribute("data-hair-layer"),
    ]);
    const rearHairIndex = childLayers.findIndex(([layer, hairLayer]) => layer === "hair" && hairLayer === "rear");
    const baseIndex = childLayers.findIndex(([layer]) => layer === "base");
    const frontHairIndex = childLayers.findIndex(([layer, hairLayer]) => layer === "hair" && hairLayer === "front");

    expect(figure?.querySelector('[data-avatar-face="skin"].avatar__skin')).not.toBeNull();
    expect(rearHairIndex).toBeGreaterThanOrEqual(0);
    expect(baseIndex).toBeGreaterThan(rearHairIndex);
    expect(frontHairIndex).toBeGreaterThan(baseIndex);
  });
});
