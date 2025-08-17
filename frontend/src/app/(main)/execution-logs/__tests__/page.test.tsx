import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

// Mock Virtuoso to avoid virtualization in this test
jest.mock("react-virtuoso", () => ({ Virtuoso: ({ data, itemContent }: any) => (<div>{(data ?? []).map((d: any, i: number) => <div key={i}>{itemContent(i, d)}</div>)}</div>) }));

import LogsPage from "../page";

jest.mock("~/lib/authFetch", () => ({ useAuthFetch: () => async () => ({ ok: true, json: async () => [] }) }));
jest.mock("~/lib/useRunLiveStream", () => ({ useRunLiveStream: () => ({ events: [{ ts: "t", level: "info", message: "live" }], connected: true }) }));

test("Execution Logs toggles to live mode", async () => {
  render(<LogsPage /> as any);
  const toggle = await screen.findByLabelText(/live/i);
  fireEvent.click(toggle);
  await waitFor(() => expect(screen.getByText(/live/)).toBeInTheDocument());
});

