import React from "react";
import { render, screen, act } from "@testing-library/react";

// Mock stack to avoid ESM deps
jest.mock("@stackframe/stack", () => ({ useUser: () => ({ getAuthJson: async () => ({ accessToken: "tok" }), selectedTeam: { id: "t" } }) }));
// Mock Virtuoso to render plain DOM
jest.mock("react-virtuoso", () => ({ Virtuoso: ({ data, itemContent }: any) => (<div>{(data ?? []).map((d: any, i: number) => <div key={i}>{itemContent(i, d)}</div>)}</div>) }));

// Mock EventSource
class MockEventSource {
  static last: MockEventSource | null = null;
  onopen: ((e: any) => void) | null = null;
  onmessage: ((e: any) => void) | null = null;
  onerror: ((e: any) => void) | null = null;
  constructor(public url: string) { MockEventSource.last = this; }
  close() {}
  triggerOpen() { this.onopen && this.onopen({}); }
  trigger(obj: any) { this.onmessage && this.onmessage({ data: JSON.stringify(obj) }); }
}
// @ts-ignore
global.EventSource = MockEventSource;

const { useRunLiveStream } = require("../useRunLiveStream");

function HookView({ runId }: { runId: string }) {
  const { events, connected } = useRunLiveStream(runId);
  return (
    <div>
      <div data-testid="connected">{String(connected)}</div>
      <div data-testid="count">{events.length}</div>
      <div data-testid="last">{events[events.length - 1]?.message ?? ""}</div>
    </div>
  );
}

test("useRunLiveStream appends log and complete", async () => {
  render(<HookView runId="run-1" />);
  // wait a tick for the hook's async effect to attach handlers
  await act(async () => { await new Promise((r) => setTimeout(r, 0)); });
  act(() => { MockEventSource.last?.triggerOpen(); });
  act(() => { MockEventSource.last?.trigger({ type: "log", ts: "t1", level: "info", message: "hello" }); });
  act(() => { MockEventSource.last?.trigger({ type: "complete", ts: "t2", output: { ok: true } }); });

  expect(screen.getByTestId("connected").textContent).toBe("true");
  expect(Number(screen.getByTestId("count").textContent)).toBeGreaterThanOrEqual(2);
  expect(screen.getByTestId("last").textContent).toMatch(/complete:/i);
});

