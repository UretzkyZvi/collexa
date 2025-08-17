import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

jest.mock("~/lib/authFetch", () => ({ useAuthFetch: () => async () => ({ ok: true, json: async () => ({ agent_id: "a1", instructions: [
  { id: "n8n", label: "n8n (HTTP Request)", language: "text", code: "URL: https://api.<host>/v1/agents/<agent-id>/invoke" },
  { id: "make", label: "Make.com (HTTP)", language: "text", code: "POST https://api.<host>/v1/agents/<agent-id>/invoke" },
] }) }) }));

import InstructionsPage from "../page";

Object.defineProperty(window, 'location', { value: { host: 'localhost:3000' } });

test("Instructions page renders and copies with placeholders", async () => {
  render(<InstructionsPage params={{ id: "agent-xyz" }} /> as any);

  // Wait for content
  await screen.findByText(/Instructions Pack/i);
  expect(screen.getByText(/n8n/)).toBeInTheDocument();

  // Spy on clipboard
  const writeText = jest.fn();
  Object.assign(navigator, { clipboard: { writeText } });

  // Click copy on first section
  fireEvent.click(screen.getAllByText(/copy/i)[0]);
  await waitFor(() => expect(writeText).toHaveBeenCalled());
  const copied = writeText.mock.calls[0][0];
  expect(copied).toMatch(/api\.localhost:3000/);
  expect(copied).toMatch(/agents\/agent-xyz\/invoke/);
});

