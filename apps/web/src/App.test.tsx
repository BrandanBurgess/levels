import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { EmptyState, ErrorState, LoadingState } from "./ui/AsyncState";

describe("App shell", () => {
  it("renders accessible desktop and mobile navigation", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Ready for today" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary navigation" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Mobile navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveAttribute(
      "href",
      "#main-content",
    );
  });

  it("navigates with hash-safe links", () => {
    render(<App />);

    fireEvent.click(screen.getAllByRole("link", { name: "Journal" })[0]!);
    expect(screen.getByRole("heading", { name: "Journal" })).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("link", { name: "More" })[0]!);
    expect(screen.getByRole("heading", { name: "More" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Library/ }).length).toBeGreaterThan(0);
  });
});

describe("shared async states", () => {
  it("announces loading, errors, retries, and empty content", () => {
    let retried = false;
    const { rerender } = render(<LoadingState />);
    expect(screen.getByRole("status")).toHaveTextContent("Waking up your training data…");

    rerender(<ErrorState message="Training data is unavailable." onRetry={() => (retried = true)} />);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retried).toBe(true);

    rerender(<EmptyState title="No sessions yet">Your first workout will appear here.</EmptyState>);
    expect(screen.getByRole("heading", { name: "No sessions yet" })).toBeInTheDocument();
  });
});
