import { render, screen, cleanup } from "@testing-library/react";
import { describe, it, expect, afterEach } from "vitest";
import { Card } from "@/components/ui/Card";

afterEach(() => {
  cleanup();
});

describe("Card", () => {
  it("renders children correctly", () => {
    render(<Card>Test Content</Card>);
    expect(screen.getByText("Test Content")).toBeInTheDocument();
  });

  it("applies default variant classes", () => {
    render(<Card data-testid="card">Content</Card>);
    const card = screen.getByTestId("card");
    expect(card).toHaveClass("bg-white/5");
    expect(card).toHaveClass("border-white/10");
  });

  it("applies elevated variant classes", () => {
    render(
      <Card variant="elevated" data-testid="card">
        Content
      </Card>
    );
    const card = screen.getByTestId("card");
    expect(card).toHaveClass("bg-white/10");
    expect(card).toHaveClass("border-white/20");
  });

  it("merges custom className", () => {
    render(
      <Card className="custom-class" data-testid="card">
        Content
      </Card>
    );
    const card = screen.getByTestId("card");
    expect(card).toHaveClass("custom-class");
  });
});
