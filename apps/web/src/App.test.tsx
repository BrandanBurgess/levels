import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("renders the LEVELS foundation", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "LEVELS" })).toBeInTheDocument();
  });
});
