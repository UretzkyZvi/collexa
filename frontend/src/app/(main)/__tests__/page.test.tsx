import { render, screen, waitFor } from "@testing-library/react";
import { Providers } from "~/test-utils/Providers";
import HomePage from "../page";

// Mock useAuthFetch
const mockAuthFetch = jest.fn();
jest.mock("~/lib/authFetch", () => ({
  useAuthFetch: () => mockAuthFetch,
}));

describe("HomePage", () => {
  beforeEach(() => {
    mockAuthFetch.mockClear();
  });

  it("renders dashboard with loading state", () => {
    mockAuthFetch.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(<Providers><HomePage /></Providers>);

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    // Should show skeleton loading states (query by data-slot attribute)
    expect(document.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0);
  });

  it("displays metrics when data is loaded", async () => {
    // Mock agents response
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { id: "agent-1", display_name: "Test Agent 1" },
        { id: "agent-2", display_name: "Test Agent 2" },
      ],
    });

    // Mock metrics response
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        org_id: "org1",
        api_calls: {
          total: 150,
          errors: 5,
          success_rate: 0.967,
        },
        request_duration_ms: {
          count: 150,
          p50: 45.2,
          p95: 120.5,
          p99: 250.1,
          avg: 67.3,
        },
        agent_invocations: {
          total: 25,
          duration_ms: {
            count: 25,
            p50: 1200.0,
            p95: 2500.0,
            p99: 3000.0,
            avg: 1450.5,
          },
        },
      }),
    });

    render(<Providers><HomePage /></Providers>);

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument(); // Agent count
    });

    // Check API calls metrics
    expect(screen.getByTestId("api-calls-total")).toHaveTextContent("150");
    expect(screen.getByText("5 errors")).toBeInTheDocument();
    expect(screen.getByText("96.7%")).toBeInTheDocument(); // Success rate

    // Check performance metrics
    expect(screen.getByText("67.3ms")).toBeInTheDocument(); // Average duration
    expect(screen.getByText("45.2ms")).toBeInTheDocument(); // P50
    expect(screen.getByText("120.5ms")).toBeInTheDocument(); // P95
    expect(screen.getByText("250.1ms")).toBeInTheDocument(); // P99

    // Check agent invocations
    expect(screen.getByText("25")).toBeInTheDocument(); // Total invocations
    expect(screen.getByText("1450.5ms")).toBeInTheDocument(); // Avg duration
  });

  it("shows welcome message for new users", async () => {
    // Mock empty agents response
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    });

    // Mock empty metrics response
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        org_id: "org1",
        api_calls: { total: 0, errors: 0, success_rate: 1.0 },
        request_duration_ms: { count: 0, p50: 0, p95: 0, p99: 0, avg: 0 },
        agent_invocations: { total: 0, duration_ms: { count: 0, p50: 0, p95: 0, p99: 0, avg: 0 } },
      }),
    });

    render(<Providers><HomePage /></Providers>);

    await waitFor(() => {
      expect(screen.getByText("Welcome to Collexa! 🎉")).toBeInTheDocument();
    });

    expect(screen.getByText("Create Your First Agent")).toBeInTheDocument();
    expect(screen.getByText(/Collexa helps you create and manage AI agents/)).toBeInTheDocument();
  });

  it("handles API errors gracefully", async () => {
    // Mock failed responses
    mockAuthFetch.mockRejectedValue(new Error("API Error"));

    render(<HomePage />);

    // Wait until content switches from skeleton to final cards by waiting for the metric testid
    const countNode = await screen.findByTestId("agents-count");
    expect(countNode).toHaveTextContent("0");
  });

  it("shows performance metrics only when there is data", async () => {
    // Mock agents response
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: "agent-1", display_name: "Test Agent" }],
    });

    // Mock metrics with no API calls
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        org_id: "org1",
        api_calls: { total: 0, errors: 0, success_rate: 1.0 },
        request_duration_ms: { count: 0, p50: 0, p95: 0, p99: 0, avg: 0 },
        agent_invocations: { total: 0, duration_ms: { count: 0, p50: 0, p95: 0, p99: 0, avg: 0 } },
      }),
    });

    render(<Providers><HomePage /></Providers>);

    await waitFor(() => {
      expect(screen.getByText("1")).toBeInTheDocument(); // Agent count
    });

    // Performance metrics section should not be visible when no API calls
    expect(screen.queryByText("Request Performance")).not.toBeInTheDocument();
    expect(screen.queryByText("Agent Invocations")).not.toBeInTheDocument();
  });
});
