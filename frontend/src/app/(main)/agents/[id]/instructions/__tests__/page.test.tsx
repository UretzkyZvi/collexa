import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

jest.mock("~/lib/authFetch", () => ({ useAuthFetch: () => async () => ({ ok: true, json: async () => ({ agent_id: "a1", instructions: [
  { id: "n8n", label: "n8n (HTTP Request)", language: "text", code: "URL: https://api.<host>/v1/agents/<agent-id>/invoke" },
  { id: "make", label: "Make.com (HTTP)", language: "text", code: "POST https://api.<host>/v1/agents/<agent-id>/invoke" },
] }) }) }));

jest.mock("next/navigation", () => ({
  useRouter: () => ({ replace: jest.fn() }),
  useParams: () => ({ id: "agent-xyz" }),
}));
import InstructionsPage from "../page";
test("Instructions page renders and copies with placeholders", async () => {
  render(<InstructionsPage />);

  // Wait for content
  await screen.findByText(/Instructions Pack/i);
  await screen.findByText(/n8n/);

  // Spy on clipboard
  const writeText = jest.fn();
  Object.assign(navigator, { clipboard: { writeText } });

  // Click copy on first section
  const copyButtons = await screen.findAllByText(/copy/i);
  fireEvent.click(copyButtons[0] as HTMLElement);
  await waitFor(() => expect(writeText).toHaveBeenCalled());
  const copied = writeText.mock.calls[0][0];
  const host = window.location.host;
  expect(copied).toContain(`api.${host}`);

  expect(copied).toMatch(/agents\/agent-xyz\/invoke/);
});

