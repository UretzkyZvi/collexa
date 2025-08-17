import React from "react";
import '@testing-library/jest-dom'
import { render, screen } from "@testing-library/react";

// Mock Virtuoso to render all items without virtualization in tests
jest.mock("react-virtuoso", () => ({ Virtuoso: ({ data, itemContent }: any) => (<div>{(data ?? []).map((d: any, i: number) => <div key={i}>{itemContent(i, d)}</div>)}</div>) }));

import { LogViewer } from "../LogViewer";

test("LogViewer renders many items (virtualized)", () => {
  const events = Array.from({ length: 2000 }, (_, i) => ({ ts: `2025-01-01T00:00:${String(i%60).padStart(2,"0")}Z`, level: "info", message: `m${i}` }));
  render(<div style={{height: 400}}><LogViewer events={events} /></div>);
  // Ensure multiple items rendered by checking a unique tail item text
  expect(screen.getByText(/m1999\b/)).toBeInTheDocument();
});

