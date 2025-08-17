import { render, screen } from "@testing-library/react";
import { CodeBlock } from "../CodeBlock";

describe("CodeBlock", () => {
  it("renders plain text pre for language=text", () => {
    render(<CodeBlock language="text" code="hello" />);
    expect(screen.getByText("hello")).toBeInTheDocument();
  });
});

